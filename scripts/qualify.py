#!/usr/bin/env python3
"""Requalify immutable completed native inputs."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "engine"


def module(name, path):
    existing = sys.modules.get(name)
    if existing is not None and Path(existing.__file__).resolve() == path.resolve():
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


ARTIFACT = module("qualify_artifact", PACKAGE / "artifact.py")


def verify_source_tree(build, package, lock, archive):
    observed, _ = ARTIFACT.source_archive_members(archive)
    source = module("qualify_source_archive", package / "build_support/source_archive.py")
    entries = source.source_entries(build, package, lock, build / "third-party")
    ARTIFACT.require(set(entries) == set(observed), "Completed source tree membership differs from source archive")
    for name, path in entries.items():
        record = observed[name]
        if "symlink" in record:
            ARTIFACT.require(path.is_symlink() and os.readlink(path) == record["symlink"],
                             "Completed source symlink differs: " + name)
        else:
            ARTIFACT.regular(path)
            ARTIFACT.require(path.stat().st_size == record["bytes"] and ARTIFACT.digest(path) == record["sha256"],
                             "Completed source file differs: " + name)


def prepare(build, scratch, package):
    frozen = scratch / "inputs"
    lock = ARTIFACT.snapshot_inputs(package, frozen)
    original_lock = ARTIFACT.snapshot_inputs(build / "inputs", scratch / "original-inputs")
    ARTIFACT.require(lock == original_lock and (frozen / "source-lock.json").read_bytes() ==
                     (build / "inputs/source-lock.json").read_bytes(), "Completed build inputs differ from current source lock")
    artifact = scratch / "artifact"
    artifact.mkdir()
    for source, name in ((build / "opengrep-source.tar.gz", "opengrep-source.tar.gz"),
                         (frozen / "source-lock.json", "source-lock.json"),
                         (build / "runtime/runtime.json", "runtime.json"),
                         (build / "platform-checks.json", "platform-checks.json")):
        shutil.copy2(ARTIFACT.regular(source), artifact / name)
    license_bytes = ARTIFACT.archive_license(artifact, lock, ARTIFACT.digest(frozen / "source-lock.json"))
    (artifact / "LICENSE").write_bytes(license_bytes)
    verify_source_tree(build, frozen, lock, artifact / "opengrep-source.tar.gz")
    binary = ARTIFACT.regular(build / "engine/cli/opengrep")
    binary_hash = ARTIFACT.digest(binary)
    ARTIFACT.require(os.access(binary, os.X_OK), "Completed executable is not executable")
    ARTIFACT.validate_platform(artifact, frozen, ("darwin", "arm64"), binary_hash)
    cli = scratch / "cli"
    cli.mkdir()
    shutil.copy2(binary, cli / "opengrep")
    distribution = build / "engine/cli/entrypoint.dist"
    ARTIFACT.require(stat.S_ISDIR(distribution.lstat().st_mode), "Completed standalone distribution is not a directory")
    shutil.copytree(distribution, cli / "entrypoint.dist", symlinks=True)
    ARTIFACT.require(ARTIFACT.digest(cli / "opengrep") == binary_hash, "Completed executable changed while copying")
    return frozen, lock, artifact, cli, binary_hash


def inspect_runtime(scratch, package, cli, profile, env):
    signing = module("qualify_signing", package / "signing/signing.py")
    runtime = module("qualify_runtime", package / "build_support/runtime.py")
    target = ARTIFACT.read_json(package / "locks/runtimes.json")["macos"]["deployment_target"]
    runtime.validate_macos(cli, target)
    helper = signing.compile_inspector(scratch / "signature-inspector")
    capacity = signing.execution_support().TestCapacity.detect()
    result = signing.execution_support().run_test_process([str(cli / "opengrep"), "--version"], env=env, cwd=scratch,
                                      timeout=capacity.deadline(120))
    ARTIFACT.require(not result.timed_out and result.returncode == 0, "Completed executable version check failed")
    extracted = list((scratch / "cache/opengrep").iterdir())
    ARTIFACT.require(len(extracted) == 1 and extracted[0].is_dir() and not extracted[0].is_symlink(),
                     "Fresh executable extraction is missing or ambiguous")
    required = ("opengrep.bin", "semgrep/bin/opengrep-core")
    standalone = signing.inspect_inventory(helper, cli / "entrypoint.dist", profile, required=required)
    extracted_images = signing.inspect_inventory(helper, extracted[0], profile, required=required)
    record = {"profile": profile.record(), "profile_sha256": profile.digest(),
              "outer": signing.inspect_image(helper, cli / "opengrep", profile),
              "standalone": standalone, "extracted": extracted_images}
    signing.validate_signing_record(record, profile, ARTIFACT.digest(cli / "opengrep"), (cli / "opengrep").stat().st_size)
    return signing, helper, extracted[0], record, result.stdout.strip()


def run_contracts(build, package, cli, artifact, scratch, env):
    python = build / "python/bin/python"
    ARTIFACT.require(python.is_file() and os.access(python, os.X_OK), "Completed build Python is unavailable")
    command = [str(python), str(package / "verify.py"), str(cli / "opengrep")]
    print("Running all frozen contracts; report: " + str(artifact / "contracts.jsonl"), file=sys.stderr, flush=True)
    execution = module("qualify_execution", package / "build_support/test_execution.py")
    with (artifact / "contracts.jsonl").open("x") as report, (scratch / "contracts.stderr.log").open("x") as errors:
        with execution.test_run_signals():
            process = subprocess.Popen(command, stdout=report, stderr=errors, env=env, cwd=scratch, start_new_session=True)
            try:
                returncode = process.wait()
            finally:
                if process.poll() is None:
                    process.send_signal(signal.SIGTERM)
                    try:
                        process.wait(timeout=execution.TestCapacity.detect().deadline(30))
                    except subprocess.TimeoutExpired:
                        execution.stop_test_process(process)
                        process.wait()
    ARTIFACT.require(returncode == 0, "Frozen contracts failed; inspect retained qualification report")
    ARTIFACT.validate_contracts(artifact / "contracts.jsonl", ARTIFACT.expected_contracts(package))


def finalize(build, scratch, package, lock, artifact, cli, binary_hash, profile, inspected):
    signing, helper, extracted, record, version = inspected
    expected_version = f'{lock["upstream_version"]}+paintedwolf.{lock["patch_version"]}'
    ARTIFACT.require(version == expected_version, "Completed executable reports a different version")
    for binary in (build / "engine/cli/opengrep", cli / "opengrep"):
        ARTIFACT.require(ARTIFACT.digest(binary) == binary_hash, "Completed executable changed during qualification")
    verify_source_tree(build, package, lock, artifact / "opengrep-source.tar.gz")
    signing.verify_inventory_unchanged(cli / "entrypoint.dist", record["standalone"])
    signing.verify_inventory_unchanged(extracted, record["extracted"])
    signing.validate_signing_record(record, profile, binary_hash, (cli / "opengrep").stat().st_size)
    shutil.copy2(cli / "opengrep", artifact / "opengrep")
    shutil.copy2(cli / "platform-checks.json", artifact / "platform-checks.json")
    provenance = {"schema_version": 1, "upstream_revision": lock["revision"],
                  "source_lock_sha256": ARTIFACT.digest(package / "source-lock.json"),
                  "platform": "darwin", "architecture": "arm64", "version": version, "signing": record}
    for name, key in (("opengrep", "binary"), ("opengrep-source.tar.gz", "source_archive"),
                      ("contracts.jsonl", "contracts"), ("platform-checks.json", "platform_checks"), ("runtime.json", "runtime")):
        provenance[key + "_sha256"] = ARTIFACT.digest(artifact / name)
        if key in ("binary", "source_archive"):
            provenance[key + "_bytes"] = (artifact / name).stat().st_size
    (artifact / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    admission_profile = ARTIFACT.signing_module().SigningProfile.parse(profile.record(), platform="darwin")
    ARTIFACT.validate_artifact(artifact, package, lock, ("darwin", "arm64"), profile=admission_profile,
                               inspect=lambda binary: signing.inspect_image(helper, binary, profile))


def qualify(build, output, profile_path, package=PACKAGE):
    ARTIFACT.require(ARTIFACT.native_target() == ("darwin", "arm64"), "Native qualification requires macOS arm64")
    ARTIFACT.require(not output.exists() and not output.is_symlink(), "Qualification output directory must be new")
    ARTIFACT.require(not output.is_relative_to(build) and not output.is_relative_to(package),
                     "Qualification output must be outside the completed build and source package")
    scratch = Path(tempfile.mkdtemp(prefix="pwog-qualify-", dir="/tmp")).resolve()
    print("Qualification workspace: " + str(scratch), file=sys.stderr, flush=True)
    try:
        frozen, lock, artifact, cli, binary_hash = prepare(build, scratch, package)
        signing = module("qualify_signing", frozen / "signing/signing.py")
        profile = signing.SigningProfile.parse(ARTIFACT.read_json(profile_path), platform="darwin")
        (scratch / "tmp").mkdir()
        env = dict(os.environ, TMPDIR=str(scratch / "tmp"), XDG_CACHE_HOME=str(scratch / "cache"),
                   SEMGREP_SETTINGS_FILE=str(scratch / "settings.yaml"), SEMGREP_SEND_METRICS="off")
        inspected = inspect_runtime(scratch, frozen, cli, profile, env)
        ARTIFACT.require(inspected[-1] == f'{lock["upstream_version"]}+paintedwolf.{lock["patch_version"]}',
                         "Completed executable reports a different version")
        run_contracts(build, frozen, cli, artifact, scratch, env)
        finalize(build, scratch, frozen, lock, artifact, cli, binary_hash, profile, inspected)
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(artifact, output)
    except BaseException:
        print("Qualification failed; workspace retained: " + str(scratch), file=sys.stderr, flush=True)
        raise
    shutil.rmtree(scratch)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--signing-profile", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = qualify(args.build_directory.resolve(strict=True), args.output.resolve(), args.signing_profile.resolve(strict=True))
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, "Native qualification: " + str(error) + "\n")
    print(result)


if __name__ == "__main__":
    main()
