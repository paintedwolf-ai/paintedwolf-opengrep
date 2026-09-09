"""Exercise native release packaging with a small executable distribution."""
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("integration_native_release", ROOT / "engine/build_support/native_release.py")
NATIVE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(NATIVE)
EXECUTION = NATIVE.SIGNING.execution_support()
VERSION = "native packaging fixture"


def checked(command, capacity, *, cwd=None, env=None):
    result = EXECUTION.run_test_process(command, timeout=capacity.deadline(120), cwd=cwd, env=env)
    if result.timed_out or result.returncode != 0:
        raise RuntimeError("Native fixture command failed: " + json.dumps(result.record()))
    return result


def exercise(root):
    capacity = EXECUTION.TestCapacity.detect()
    profile = NATIVE.SIGNING.SigningProfile.parse(None)
    target = json.loads((NATIVE.PACKAGE / "locks/runtimes.json").read_text())["macos"]["deployment_target"]
    handoff = root / "initial"
    distribution = handoff / "cli/entrypoint.dist"
    (distribution / "semgrep/bin").mkdir(parents=True)
    artifact = handoff / "artifact"
    artifact.mkdir()
    sources = root / "sources"
    sources.mkdir()
    library = sources / "library.c"
    library.write_text('const char *fixture_version(void) { return "' + VERSION + '"; }\n')
    main = sources / "main.c"
    main.write_text('#include <stdio.h>\nextern const char *fixture_version(void);\n'
                    'int main(void) { puts(fixture_version()); return 0; }\n')
    core = sources / "core.c"
    core.write_text('int main(void) { return 0; }\n')
    compiler = ["xcrun", "clang", "-arch", "arm64", "-mmacosx-version-min=" + target]
    checked([*compiler, "-dynamiclib", str(library), "-Wl,-install_name,@rpath/libfixture.dylib",
             "-o", str(distribution / "libfixture.dylib")], capacity)
    checked([*compiler, str(main), "-L" + str(distribution), "-lfixture", "-Wl,-rpath,@loader_path",
             "-o", str(distribution / "opengrep.bin")], capacity)
    checked([*compiler, str(core), "-o", str(distribution / "semgrep/bin/opengrep-core")], capacity)
    (distribution / "data.txt").write_text("packaged data\n")
    (distribution / "data-link").symlink_to("data.txt")
    shutil.copy2(distribution / "opengrep.bin", artifact / "opengrep")
    shutil.copy2(NATIVE.PACKAGE / "source-lock.json", artifact / "source-lock.json")
    for name in ("provenance.json", "contracts.jsonl", "opengrep-source.tar.gz", "platform-checks.json",
                 "runtime.json", "LICENSE"):
        (artifact / name).write_text("fixture " + name + "\n")
    NATIVE.check_layout(handoff)
    build_id = "paintedwolf-" + NATIVE.HANDOFF.digest(distribution / "data.txt")
    compiled = root / "compiled.tar.gz"
    NATIVE.HANDOFF.write(handoff, compiled, NATIVE.lock_hash(), "compiled", build_id)
    inspector = NATIVE.SIGNING.compile_inspector(root / "inspector", capacity)
    inner = root / "inner-signed.tar.gz"
    NATIVE.sign(compiled, inner, inspector, profile, None, None)
    packaged = root / "packaged.tar.gz"
    NATIVE.package(inner, packaged)
    outer = root / "outer-signed.tar.gz"
    NATIVE.sign(packaged, outer, inspector, profile, None, None, outer=True)
    qualified = root / "qualified"
    qualified.mkdir()
    transferred = qualified / "handoff"
    NATIVE.HANDOFF.read(outer, transferred, NATIVE.lock_hash(), "outer-signed")
    NATIVE.check_layout(transferred)
    cli = transferred / "cli"
    shutil.copy2(transferred / "artifact/opengrep", cli / "opengrep")
    (qualified / "tmp").mkdir()
    env = dict(os.environ, TMPDIR=str(qualified / "tmp"), XDG_CACHE_HOME=str(qualified / "cache"))
    _, signing, version, extracted = NATIVE.inspect(qualified, cli, profile, env, build_id)
    if version != VERSION:
        raise RuntimeError("Packaged executable returned the wrong fixture version")
    repeated = checked([cli / "opengrep", "--version"], capacity, cwd=qualified, env=env)
    if repeated.stdout.strip() != VERSION:
        raise RuntimeError("Cached executable returned the wrong fixture version")
    NATIVE.verify_distribution(cli / "entrypoint.dist", extracted)
    NATIVE.SIGNING.verify_inventory_unchanged(extracted, signing["extracted"])
    (extracted / "data.txt").write_text("changed data\n")
    try:
        NATIVE.verify_distribution(cli / "entrypoint.dist", extracted)
    except ValueError:
        pass
    else:
        raise RuntimeError("Payload verification accepted changed data")
    print("Native packaging chain passed: inner signing, compression, outer signing, extraction, cache reuse, tamper rejection")


@unittest.skipUnless(sys.platform == "darwin" and platform.machine() == "arm64", "Native packaging requires macOS arm64")
@unittest.skipUnless(os.environ.get("PW_NATIVE_PACKAGING_PYTHON"), "Set PW_NATIVE_PACKAGING_PYTHON to a prepared release Python")
class NativePackagingIntegrationTest(unittest.TestCase):
    def test_signed_distribution_survives_real_packaging(self):
        python = Path(os.environ["PW_NATIVE_PACKAGING_PYTHON"]).absolute()
        self.assertTrue(python.is_file(), "Prepared release Python does not exist")
        capacity = EXECUTION.TestCapacity.detect()
        with tempfile.TemporaryDirectory(prefix="native-packaging-test-") as temporary:
            result = EXECUTION.run_test_process([python, str(Path(__file__).resolve()), "--exercise", temporary],
                                               timeout=capacity.deadline(600), cwd=ROOT)
        self.assertFalse(result.timed_out, json.dumps(result.record()))
        self.assertEqual(result.returncode, 0, json.dumps(result.record()))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--exercise":
        exercise(Path(sys.argv[2]).resolve(strict=True))
    else:
        unittest.main()
