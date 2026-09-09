#!/usr/bin/env python3
"""Sign and qualify artifacts across isolated release jobs."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

PACKAGE = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


HANDOFF = module("native_handoff", PACKAGE / "build_support/handoff.py")
SIGNING = module("native_signing", PACKAGE / "signing/signing.py")
REQUIRED = ("opengrep.bin", "semgrep/bin/opengrep-core")


def artifact_module():
    return module("native_artifact", PACKAGE / "artifact.py")


def lock_hash():
    return HANDOFF.digest(PACKAGE / "source-lock.json")


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def check_layout(root):
    expected = {"opengrep", "provenance.json", "source-lock.json", "contracts.jsonl", "opengrep-source.tar.gz",
                "platform-checks.json", "runtime.json", "LICENSE"}
    HANDOFF.require({path.name for path in (root / "artifact").iterdir()} == expected,
                    "Unexpected native handoff artifact membership")
    for path in (root / "artifact").iterdir():
        HANDOFF.require(path.is_file() and not path.is_symlink(), "Artifact requires regular files")
    HANDOFF.require({path.name for path in (root / "cli").iterdir()} == {"entrypoint.dist"}
                    and (root / "cli/entrypoint.dist").is_dir()
                    and not (root / "cli/entrypoint.dist").is_symlink(), "Unexpected handoff distribution layout")
    HANDOFF.require((root / "artifact/source-lock.json").read_bytes() == (PACKAGE / "source-lock.json").read_bytes(),
                    "Handoff artifact source lock differs")
    images = SIGNING.image_inventory(root / "cli/entrypoint.dist")
    HANDOFF.require(set(REQUIRED).issubset(images), "Required native payload images missing")


def export(build, output):
    artifact = artifact_module()
    lock = json.loads((PACKAGE / "source-lock.json").read_text())
    HANDOFF.require((build / "inputs/source-lock.json").read_bytes() == (PACKAGE / "source-lock.json").read_bytes(),
                    "Compiled inputs differ from the checked-in source")
    profile = SIGNING.SigningProfile.parse(None)
    license_bytes = artifact.validate_artifact(build / "artifact", PACKAGE, lock, ("darwin", "arm64"),
                                               require_license=False, profile=profile)
    with tempfile.TemporaryDirectory(prefix="native-export-") as temporary:
        root = Path(temporary)
        shutil.copytree(build / "artifact", root / "artifact")
        (root / "artifact/LICENSE").write_bytes(license_bytes)
        (root / "cli").mkdir()
        distribution = root / "cli/entrypoint.dist"
        shutil.copytree(build / "engine/cli/entrypoint.dist", distribution, symlinks=True)
        check_layout(root)
        record = json.loads((root / "artifact/provenance.json").read_text())
        SIGNING.verify_inventory_unchanged(distribution, record["signing"]["standalone"])
        build_id = "paintedwolf-" + hashlib.sha256(json.dumps(HANDOFF.inventory(root), sort_keys=True).encode()).hexdigest()
        HANDOFF.write(root, output, lock_hash(), "compiled", build_id)


def codesign(path, profile, identity, keychain):
    if profile.mode == "developer-id":
        HANDOFF.require(identity and keychain, "Developer ID signing requires identity and an isolated keychain")
        command = ["/usr/bin/codesign", "--force", "--sign", identity, "--keychain", str(keychain),
                   "--timestamp", "--options", "runtime", "--identifier", "dev.paintedwolf.opengrep"]
    else:
        HANDOFF.require(not identity and not keychain, "Ad-hoc signing does not use a Developer ID key")
        command = ["/usr/bin/codesign", "--force", "--sign", "-", "--identifier", "dev.paintedwolf.opengrep"]
    command += [str(path)]
    subprocess.run(command, check=True)


def sign(input_path, output, inspector, profile, identity, keychain, outer=False):
    stage, next_stage = ("packaged", "outer-signed") if outer else ("compiled", "inner-signed")
    with tempfile.TemporaryDirectory(prefix="native-sign-") as temporary:
        root = Path(temporary) / "handoff"
        value = HANDOFF.read(input_path, root, lock_hash(), stage)
        check_layout(root)
        targets = {"artifact/opengrep": root / "artifact/opengrep"} if outer else {
            "cli/entrypoint.dist/" + name: path for name, path in SIGNING.image_inventory(root / "cli/entrypoint.dist").items()}
        before = HANDOFF.inventory(root)
        if outer:
            SIGNING.inspect_inventory(inspector, root / "cli/entrypoint.dist", profile, required=REQUIRED)
        for path in targets.values():
            codesign(path, profile, identity, keychain)
            SIGNING.inspect_image(inspector, path, profile)
        after = HANDOFF.inventory(root)
        HANDOFF.require(set(before) == set(after) and all(before[name] == after[name] for name in before if name not in targets),
                        "Signing changed files outside the native signing targets")
        HANDOFF.write(root, output, lock_hash(), next_stage, value["build_id"])


def package(input_path, output):
    packer = module("native_onefile", PACKAGE / "build_support/onefile.py")
    with tempfile.TemporaryDirectory(prefix="native-package-") as temporary:
        scratch = Path(temporary)
        root = scratch / "handoff"
        value = HANDOFF.read(input_path, root, lock_hash(), "inner-signed")
        check_layout(root)
        before = HANDOFF.inventory(root)
        target = json.loads((PACKAGE / "locks/runtimes.json").read_text())["macos"]["deployment_target"]
        packer.package(root / "cli/entrypoint.dist", scratch / "opengrep", scratch / "launcher", value["build_id"], target)
        HANDOFF.require(HANDOFF.inventory(root) == before, "Packaging changed signed input files")
        shutil.copy2(scratch / "opengrep", root / "artifact/opengrep")
        HANDOFF.write(root, output, lock_hash(), "packaged", value["build_id"])


def inspect(scratch, cli, profile, env, build_id):
    runtime = module("native_runtime", PACKAGE / "build_support/runtime.py")
    target = json.loads((PACKAGE / "locks/runtimes.json").read_text())["macos"]["deployment_target"]
    runtime.validate_macos(cli, target)
    helper = SIGNING.compile_inspector(scratch / "signature-inspector")
    outer = SIGNING.inspect_image(helper, cli / "opengrep", profile)
    standalone = SIGNING.inspect_inventory(helper, cli / "entrypoint.dist", profile, required=REQUIRED)
    capacity = SIGNING.execution_support().TestCapacity.detect()
    result = SIGNING.execution_support().run_test_process([str(cli / "opengrep"), "--version"], cwd=scratch, env=env,
                                      timeout=capacity.deadline(120))
    (scratch / "version.stdout.log").write_text(result.stdout)
    (scratch / "version.stderr.log").write_text(result.stderr)
    write_json(scratch / "version.json", {"returncode": result.returncode, "timed_out": result.timed_out})
    HANDOFF.require(not result.timed_out and result.returncode == 0, "Final native version check failed")
    extracted = scratch / "cache/opengrep" / build_id
    HANDOFF.require(extracted.is_dir() and not extracted.is_symlink()
                    and list(extracted.parent.iterdir()) == [extracted], "Native extraction identity mismatch")
    verify_distribution(cli / "entrypoint.dist", extracted)
    extracted_images = SIGNING.inspect_inventory(helper, extracted, profile, required=REQUIRED)
    record = {"profile": profile.record(), "profile_sha256": profile.digest(), "outer": outer,
              "standalone": standalone, "extracted": extracted_images}
    write_json(scratch / "signing.json", record)
    SIGNING.validate_signing_record(record, profile, HANDOFF.digest(cli / "opengrep"), (cli / "opengrep").stat().st_size)
    return helper, record, result.stdout.strip(), extracted


def verify_distribution(standalone, extracted):
    prefix = "cli/entrypoint.dist"
    HANDOFF.require(HANDOFF.inventory(standalone, prefix=prefix) == HANDOFF.inventory(extracted, prefix=prefix),
                    "Extracted payload differs from the signed distribution")


def contracts(binary, report, scratch, env):
    execution = SIGNING.execution_support()
    with report.open("w") as output, (scratch / "contracts.stderr.log").open("w") as errors:
        with execution.test_run_signals():
            process = subprocess.Popen([sys.executable, str(PACKAGE / "verify.py"), str(binary)],
                                       stdout=output, stderr=errors, cwd=scratch, env=env, start_new_session=True)
            try:
                code = process.wait()
            finally:
                if process.poll() is None:
                    execution.stop_test_process(process)
                    process.wait()
    HANDOFF.require(code == 0, "Frozen native contracts failed; see " + str(scratch / "contracts.stderr.log"))


def retain_diagnostics(scratch, output, error):
    output.mkdir(parents=True)
    files = {}
    for name in ("version.stdout.log", "version.stderr.log", "version.json", "signing.json",
                 "contracts.jsonl", "contracts.stderr.log", "handoff/cli/platform-checks.json"):
        source = scratch / name
        if source.is_symlink() or not source.is_file():
            continue
        with source.open("rb") as stream:
            size = stream.seek(0, os.SEEK_END)
            stream.seek(max(0, size - 4 * 1024 * 1024))
            data = stream.read(4 * 1024 * 1024)
        (output / source.name).write_bytes(data)
        files[source.name] = {"bytes": size, "retained_bytes": len(data), "truncated": size > len(data)}
    write_json(output / "failure.json", {"error_type": type(error).__name__, "error": str(error), "files": files})


def verify(input_path, output, profile, diagnostics):
    artifact = artifact_module()
    HANDOFF.require(not output.exists() and not output.is_symlink(), "Qualification output must be new")
    HANDOFF.require(not diagnostics.exists() and not diagnostics.is_symlink(), "Diagnostics output must be new")
    scratch = Path(tempfile.mkdtemp(prefix="native-verify-")).resolve()
    print("Qualification workspace: " + str(scratch), file=sys.stderr, flush=True)
    try:
        root = scratch / "handoff"
        value = HANDOFF.read(input_path, root, lock_hash(), "outer-signed")
        check_layout(root)
        expected = HANDOFF.inventory(root)
        cli, artifacts = root / "cli", root / "artifact"
        shutil.copy2(artifacts / "opengrep", cli / "opengrep")
        (scratch / "tmp").mkdir()
        env = dict(os.environ, TMPDIR=str(scratch / "tmp"), XDG_CACHE_HOME=str(scratch / "cache"),
                   SEMGREP_SETTINGS_FILE=str(scratch / "settings.yaml"), SEMGREP_SEND_METRICS="off")
        helper, signing, version, extracted = inspect(scratch, cli, profile, env, value["build_id"])
        lock = json.loads((PACKAGE / "source-lock.json").read_text())
        HANDOFF.require(version == f'{lock["upstream_version"]}+paintedwolf.{lock["patch_version"]}',
                        "Final executable version differs from source lock")
        contracts(cli / "opengrep", scratch / "contracts.jsonl", scratch, env)
        verify_distribution(cli / "entrypoint.dist", extracted)
        SIGNING.verify_inventory_unchanged(cli / "entrypoint.dist", signing["standalone"])
        SIGNING.verify_inventory_unchanged(extracted, signing["extracted"])
        actual = HANDOFF.inventory(root)
        HANDOFF.require(all(actual.get(name) == facts for name, facts in expected.items()),
                        "Native handoff files changed during qualification")
        HANDOFF.require(HANDOFF.digest(cli / "opengrep") == expected["artifact/opengrep"]["sha256"],
                        "Qualified executable changed during execution")
        shutil.copy2(cli / "platform-checks.json", artifacts / "platform-checks.json")
        shutil.copy2(scratch / "contracts.jsonl", artifacts / "contracts.jsonl")
        provenance = {"schema_version": 1, "upstream_revision": lock["revision"], "source_lock_sha256": lock_hash(),
                      "platform": "darwin", "architecture": "arm64", "version": version, "signing": signing}
        for name, key in (("opengrep", "binary"), ("opengrep-source.tar.gz", "source_archive"), ("contracts.jsonl", "contracts"),
                          ("platform-checks.json", "platform_checks"), ("runtime.json", "runtime")):
            provenance[key + "_sha256"] = HANDOFF.digest(artifacts / name)
            if key in ("binary", "source_archive"):
                provenance[key + "_bytes"] = (artifacts / name).stat().st_size
        write_json(artifacts / "provenance.json", provenance)
        artifact.validate_artifact(artifacts, PACKAGE, lock, ("darwin", "arm64"), profile=profile,
                                   inspect=lambda path: SIGNING.inspect_image(helper, path, profile))
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(artifacts, output)
    except BaseException as error:
        try:
            retain_diagnostics(scratch, diagnostics, error)
        except OSError as diagnostic_error:
            print("Could not retain qualification diagnostics: " + str(diagnostic_error), file=sys.stderr)
        print("Qualification failed; retained workspace: " + str(scratch), file=sys.stderr, flush=True)
        raise
    shutil.rmtree(scratch)


def prepare_python(output):
    HANDOFF.require(not output.exists() and not output.is_symlink(), "Python environment must be new")
    dependencies = module("native_dependencies", PACKAGE / "build_support/dependencies.py")
    subprocess.run([sys.executable, "-m", "venv", str(output)], check=True)
    with tempfile.TemporaryDirectory(prefix="native-python-downloads-") as temporary:
        dependencies.fetch_python(PACKAGE, Path(temporary))
        dependencies.install_python(output / "bin/python", PACKAGE, Path(temporary))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("prepare-python")
    command.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("export")
    command.add_argument("--build-directory", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    for name in ("sign-inner", "package", "sign-outer", "verify"):
        command = commands.add_parser(name)
        command.add_argument("--input", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True)
        if name != "package":
            command.add_argument("--signing-profile", type=Path, required=True)
        if name == "verify":
            command.add_argument("--diagnostics", type=Path, required=True)
        if name.startswith("sign-"):
            command.add_argument("--inspector", type=Path, required=True)
            command.add_argument("--identity")
            command.add_argument("--keychain", type=Path)
    args = parser.parse_args()
    try:
        HANDOFF.require(sys.platform == "darwin" and os.uname().machine == "arm64", "Native release requires macOS arm64")
        if args.command == "prepare-python":
            prepare_python(args.output.resolve())
        elif args.command == "export":
            export(args.build_directory.resolve(strict=True), args.output.resolve())
        elif args.command == "package":
            package(args.input.resolve(strict=True), args.output.resolve())
        else:
            profile = SIGNING.SigningProfile.parse(json.loads(args.signing_profile.read_text()))
            if args.command == "verify":
                verify(args.input.resolve(strict=True), args.output.resolve(), profile, args.diagnostics.resolve())
            else:
                sign(args.input.resolve(strict=True), args.output.resolve(), args.inspector.resolve(strict=True), profile,
                     args.identity, args.keychain, outer=args.command == "sign-outer")
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, "Native release: " + str(error) + "\n")


if __name__ == "__main__":
    main()
