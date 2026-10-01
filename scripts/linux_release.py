#!/usr/bin/env python3
"""Hand a Linux engine from its compile job to a fresh qualification job.

A Linux engine is the onefile executable the build produced; it carries no code
signature, and the release attestations bind its bytes. Qualification on a clean
runner extracts it, regenerates the platform report from the extracted images and
the standalone distribution, requires the build's report to match, and runs every
frozen contract against the executable.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

PACKAGE = Path(__file__).resolve().parents[1] / "engine"
TARGET = ("linux", "amd64")
ARTIFACT_MEMBERS = {"opengrep", "provenance.json", "source-lock.json", "contracts.jsonl", "opengrep-source.tar.gz",
                    "platform-checks.json", "runtime.json", "LICENSE"}


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


HANDOFF = module("linux_handoff", PACKAGE / "build_support/handoff.py")
RUNTIME = module("linux_runtime", PACKAGE / "build_support/runtime.py")
EXECUTION = module("linux_test_execution", PACKAGE / "build_support/test_execution.py")


def artifact_module():
    return module("linux_artifact", PACKAGE / "artifact.py")


def lock_hash():
    return HANDOFF.digest(PACKAGE / "source-lock.json")


def check_layout(root):
    HANDOFF.require({path.name for path in (root / "artifact").iterdir()} == ARTIFACT_MEMBERS,
                    "Unexpected Linux handoff artifact membership")
    for path in (root / "artifact").iterdir():
        HANDOFF.require(path.is_file() and not path.is_symlink(), "Artifact requires regular files")
    HANDOFF.require({path.name for path in (root / "cli").iterdir()} == {"entrypoint.dist"}
                    and (root / "cli/entrypoint.dist").is_dir()
                    and not (root / "cli/entrypoint.dist").is_symlink(), "Unexpected handoff distribution layout")
    HANDOFF.require((root / "artifact/source-lock.json").read_bytes() == (PACKAGE / "source-lock.json").read_bytes(),
                    "Handoff artifact source lock differs")


def export(build, output):
    """The compiled artifact, its licence, and the standalone distribution it was packed
    from, as one handoff for the qualification job."""
    artifact = artifact_module()
    lock = json.loads((PACKAGE / "source-lock.json").read_text())
    HANDOFF.require((build / "inputs/source-lock.json").read_bytes() == (PACKAGE / "source-lock.json").read_bytes(),
                    "Compiled inputs differ from the checked-in source")
    license_bytes = artifact.validate_artifact(build / "artifact", PACKAGE, lock, TARGET, require_license=False)
    with tempfile.TemporaryDirectory(prefix="linux-export-") as temporary:
        root = Path(temporary)
        shutil.copytree(build / "artifact", root / "artifact")
        (root / "artifact/LICENSE").write_bytes(license_bytes)
        (root / "cli").mkdir()
        shutil.copytree(build / "engine/cli/entrypoint.dist", root / "cli/entrypoint.dist", symlinks=True)
        check_layout(root)
        build_id = "paintedwolf-" + hashlib.sha256(json.dumps(HANDOFF.inventory(root), sort_keys=True).encode()).hexdigest()
        HANDOFF.write(root, output, lock_hash(), "compiled", build_id)


def run_version(cli, scratch, env):
    capacity = EXECUTION.TestCapacity.detect()
    result = EXECUTION.run_test_process([str(cli / "opengrep"), "--version"], cwd=scratch, env=env,
                                        timeout=capacity.deadline(120))
    (scratch / "version.stdout.log").write_text(result.stdout)
    (scratch / "version.stderr.log").write_text(result.stderr)
    HANDOFF.require(not result.timed_out and result.returncode == 0, "Final Linux version check failed")
    extractions = list((scratch / "cache/opengrep").iterdir())
    HANDOFF.require(len(extractions) == 1 and extractions[0].is_dir() and not extractions[0].is_symlink(),
                    "Linux extraction identity mismatch")
    return result.stdout.strip(), extractions[0]


def contracts(binary, report, scratch, env):
    with report.open("w") as output, (scratch / "contracts.stderr.log").open("w") as errors:
        with EXECUTION.test_run_signals():
            process = subprocess.Popen([sys.executable, str(PACKAGE / "verify.py"), str(binary)],
                                       stdout=output, stderr=errors, cwd=scratch, env=env, start_new_session=True)
            try:
                code = process.wait()
            finally:
                if process.poll() is None:
                    EXECUTION.stop_test_process(process)
                    process.wait()
    HANDOFF.require(code == 0, "Frozen contracts failed; see " + str(scratch / "contracts.stderr.log"))


def retain_diagnostics(scratch, output, error):
    output.mkdir(parents=True)
    files = {}
    for name in ("version.stdout.log", "version.stderr.log", "contracts.jsonl", "contracts.stderr.log",
                 "handoff/cli/platform-checks.json"):
        source = scratch / name
        if source.is_symlink() or not source.is_file():
            continue
        with source.open("rb") as stream:
            size = stream.seek(0, os.SEEK_END)
            stream.seek(max(0, size - 4 * 1024 * 1024))
            data = stream.read(4 * 1024 * 1024)
        (output / source.name).write_bytes(data)
        files[source.name] = {"bytes": size, "retained_bytes": len(data), "truncated": size > len(data)}
    (output / "failure.json").write_text(json.dumps({"error_type": type(error).__name__, "error": str(error),
                                                     "files": files}, indent=2) + "\n")


def verify(input_path, output, diagnostics):
    artifact = artifact_module()
    HANDOFF.require(not output.exists() and not output.is_symlink(), "Qualification output must be new")
    HANDOFF.require(not diagnostics.exists() and not diagnostics.is_symlink(), "Diagnostics output must be new")
    scratch = Path(tempfile.mkdtemp(prefix="linux-verify-")).resolve()
    print("Qualification workspace: " + str(scratch), file=sys.stderr, flush=True)
    try:
        root = scratch / "handoff"
        HANDOFF.read(input_path, root, lock_hash(), "compiled")
        check_layout(root)
        expected = HANDOFF.inventory(root)
        cli, artifacts = root / "cli", root / "artifact"
        shutil.copy2(artifacts / "opengrep", cli / "opengrep")
        (scratch / "tmp").mkdir()
        (scratch / "cache").mkdir()
        env = dict(os.environ, TMPDIR=str(scratch / "tmp"), XDG_CACHE_HOME=str(scratch / "cache"),
                   SEMGREP_SETTINGS_FILE=str(scratch / "settings.yaml"), SEMGREP_SEND_METRICS="off")
        version, extracted = run_version(cli, scratch, env)
        lock = json.loads((PACKAGE / "source-lock.json").read_text())
        HANDOFF.require(version == f'{lock["upstream_version"]}+paintedwolf.{lock["patch_version"]}',
                        "Final executable version differs from source lock")
        runtimes = json.loads((PACKAGE / "locks/runtimes.json").read_text())
        report = RUNTIME.validate_linux(cli, extracted, runtimes["linux"]["glibc_max"])
        HANDOFF.require(report == json.loads((artifacts / "platform-checks.json").read_text()),
                        "Qualified images differ from the build's platform report")
        contracts(cli / "opengrep", scratch / "contracts.jsonl", scratch, env)
        actual = HANDOFF.inventory(root)
        HANDOFF.require(all(actual.get(name) == facts for name, facts in expected.items()),
                        "Linux handoff files changed during qualification")
        HANDOFF.require(HANDOFF.digest(cli / "opengrep") == expected["artifact/opengrep"]["sha256"],
                        "Qualified executable changed during execution")
        shutil.copy2(scratch / "contracts.jsonl", artifacts / "contracts.jsonl")
        provenance = {"schema_version": 1, "upstream_revision": lock["revision"], "source_lock_sha256": lock_hash(),
                      "platform": "linux", "architecture": platform.machine(), "version": version, "signing": None}
        for name, key in (("opengrep", "binary"), ("opengrep-source.tar.gz", "source_archive"), ("contracts.jsonl", "contracts"),
                          ("platform-checks.json", "platform_checks"), ("runtime.json", "runtime")):
            provenance[key + "_sha256"] = HANDOFF.digest(artifacts / name)
            if key in ("binary", "source_archive"):
                provenance[key + "_bytes"] = (artifacts / name).stat().st_size
        (artifacts / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
        artifact.validate_artifact(artifacts, PACKAGE, lock, TARGET)
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
    """A clean interpreter environment with the locked Python distributions, for the
    contract runner."""
    HANDOFF.require(not output.exists() and not output.is_symlink(), "Python environment must be new")
    dependencies = module("linux_dependencies", PACKAGE / "build_support/dependencies.py")
    subprocess.run([sys.executable, "-m", "venv", str(output)], check=True)
    with tempfile.TemporaryDirectory(prefix="linux-python-downloads-") as temporary:
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
    command = commands.add_parser("verify")
    command.add_argument("--input", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--diagnostics", type=Path, required=True)
    args = parser.parse_args()
    try:
        HANDOFF.require(sys.platform == "linux" and platform.machine() == "x86_64", "Linux release requires linux/amd64")
        if args.command == "prepare-python":
            prepare_python(args.output.resolve())
        elif args.command == "export":
            export(args.build_directory.resolve(strict=True), args.output.resolve())
        else:
            verify(args.input.resolve(strict=True), args.output.resolve(), args.diagnostics.resolve())
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, "Linux release: " + str(error) + "\n")


if __name__ == "__main__":
    main()
