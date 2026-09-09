#!/usr/bin/env python3
"""Resolve a complete, source-qualified native Opengrep build artifact."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import platform
import posixpath
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile

PACKAGE = Path(__file__).resolve().parent
REQUIRED = ("opengrep", "opengrep-source.tar.gz", "source-lock.json", "provenance.json",
            "contracts.jsonl", "platform-checks.json", "runtime.json")


def signing_module():
    name = "paintedwolf_opengrep_signing"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, PACKAGE / "signing/signing.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def artifact_cache_key(source_hash, target, profile):
    return source_hash + "-" + "-".join(target) + "-" + profile.digest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with path.open("rb") as stream:
        result = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
        return result.hexdigest()


def regular(path):
    require(stat.S_ISREG(path.lstat().st_mode), f"Artifact is not a regular file: {path}")
    return path


def artifact_tree(directory):
    require(stat.S_ISDIR(directory.lstat().st_mode), f"Artifact is not a directory: {directory}")
    for path in directory.rglob("*"):
        require(stat.S_ISREG(path.lstat().st_mode) or stat.S_ISDIR(path.lstat().st_mode),
                f"Artifact contains a symlink or special file: {path}")
    for name in REQUIRED:
        regular(directory / name)


def read_json(path):
    return json.loads(regular(path).read_text())


def snapshot_inputs(package, destination):
    lock = read_json(package / "source-lock.json")
    regular(package / "build.py")
    require(digest(package / "build.py") == lock["files"]["build.py"], "Build driver differs from source lock")
    spec = importlib.util.spec_from_file_location("opengrep_artifact_build", package / "build.py")
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    return driver.snapshot_package(package, destination)


def native_target():
    system = platform.system().lower()
    arch = {"aarch64": "arm64", "x86_64": "amd64"}.get(platform.machine(), platform.machine())
    require(system in ("darwin", "linux"), f"Unsupported native build platform: {system}")
    return system, arch


def expected_contracts(package):
    root = package / "source/tests"
    translations = set(read_json(root / "rule-translation.json"))
    cases = []
    for config in sorted((root / "tainting").rglob("*.yaml")):
        sources = [p for p in config.parent.glob(config.stem + ".*") if p.suffix not in (".yaml", ".json")]
        require(sources, f"Contract has no source: {config}")
        for source in sources:
            cases.append(source.relative_to(package).as_posix())
            if config.relative_to(root).as_posix() in translations:
                cases.append("rule-translation/" + source.relative_to(root).as_posix())
    cases += ["file-selection/" + x["language"] for x in read_json(root / "native-file-selection.json")]
    for name in ("callback-rule-validation", "model-rule-validation", "native-pattern-validation"):
        cases += ["rule-validation/" + x["name"] for x in read_json(root / (name + ".json"))]
    require(cases and len(cases) == len(set(cases)), "Frozen contracts are empty or duplicate")
    return set(cases)


def complete_execution(execution, case, success=False):
    require(isinstance(execution, dict) and execution.get("timed_out") is False
            and type(execution.get("returncode")) is int and execution["returncode"] in (0, 2, 3, 7),
            f"Contract execution incomplete: {case}")
    if success:
        require(execution["returncode"] == 0, f"Contract translation failed: {case}")


def validate_contracts(path, expected):
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    require(rows and "case" not in rows[-1], "Contract summary missing")
    summary = rows.pop()
    require(type(summary.get("contracts")) is int and summary["contracts"] == len(expected)
            and type(summary.get("failed")) is int and summary["failed"] == 0,
            "Contract summary is incomplete or failed")
    seen = set()
    for row in rows:
        case = row.get("case")
        require(case in expected and case not in seen, f"Unexpected or duplicate contract: {case}")
        seen.add(case)
        require(row.get("passed") is True and not row.get("status"), f"Contract did not pass: {case}")
        require("expected" not in row or "actual" not in row or row["expected"] == row["actual"],
                f"Contract result differs from expectation: {case}")
        complete_execution(row.get("execution"), case)
        require(type(row.get("exit_code")) is int and row["exit_code"] == row["execution"]["returncode"],
                f"Contract exit status differs: {case}")
        for key in ("traces_valid", "evidence_valid", "diagnostic_paths_valid", "diagnostic_positions_valid",
                    "finding_positions_valid", "findings_unique"):
            require(key not in row or row[key] is True, f"Contract evidence invalid: {case}: {key}")
        if case.startswith("rule-translation/"):
            execution = row.get("translation_execution", {})
            for phase in ("discovery", "translation"):
                complete_execution(execution.get(phase), case, success=True)
    require(seen == expected, f"Contract cases missing: {sorted(expected - seen)}")


def archive_path(name):
    path = PurePosixPath(name)
    require(name and path.parts and "\x00" not in name and "\\" not in name and not path.is_absolute()
            and ".." not in path.parts and path.as_posix() == name,
            "Invalid source archive path: " + name)
    return path


def unique_object(pairs):
    result = {}
    for name, value in pairs:
        require(name not in result, "Duplicate source manifest key: " + name)
        result[name] = value
    return result


def source_archive_members(path):
    observed, selected = {}, {}
    wanted = {"engine/LICENSE", "SOURCE-MANIFEST.json", "inputs/source-lock.json"}
    total = 0
    with tarfile.open(path, "r|gz") as archive:
        for member in archive:
            name = member.name
            parts = archive_path(name).parts
            require(name not in observed, "Duplicate source archive member: " + name)
            require(name == "SOURCE-MANIFEST.json" or parts[0] in ("engine", "grammars", "inputs", "third-party"),
                    "Unexpected source archive root: " + name)
            require(len(observed) < 100000, "Source archive member count exceeds bound")
            if member.issym():
                require(member.size == 0, "Source archive symlink has a data payload: " + name)
                target = member.linkname
                require(target and "\x00" not in target and "\\" not in target
                        and not PurePosixPath(target).is_absolute(), "Invalid source archive symlink: " + name)
                archive_path(posixpath.normpath(posixpath.join(str(PurePosixPath(name).parent), target)))
                observed[name] = {"symlink": target}
            else:
                require(member.type in (tarfile.REGTYPE, tarfile.AREGTYPE), "Non-file source archive member: " + name)
                require(0 <= member.size <= 1024 ** 3, "Source archive member size exceeds bound: " + name)
                total += member.size
                require(total <= 8 * 1024 ** 3, "Source archive size exceeds bound")
                if name in wanted:
                    require(member.size <= 16 * 1024 ** 2, "Source archive identity exceeds size bound")
                stream, result, size, chunks = archive.extractfile(member), hashlib.sha256(), 0, []
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    result.update(block)
                    size += len(block)
                    if name in wanted:
                        chunks.append(block)
                require(size == member.size, "Truncated source archive member: " + name)
                observed[name] = {"bytes": size, "sha256": result.hexdigest()}
                if name in wanted:
                    selected[name] = b"".join(chunks)
    require(set(selected) == wanted, "Source archive identity or license missing")
    del observed["SOURCE-MANIFEST.json"]
    return observed, selected


def validate_archived_inputs(observed, lock, lock_hash):
    expected = {"inputs/" + name: value for name, value in lock["files"].items()}
    expected["inputs/source-lock.json"] = lock_hash
    actual = {name for name in observed if name.startswith("inputs/")}
    require(actual == set(expected), "Source archive locked input inventory differs")
    for name, expected_hash in expected.items():
        require(observed[name].get("sha256") == expected_hash, "Source archive locked input differs: " + name)
    for name, expected_hash in lock["files"].items():
        if name.startswith("source/"):
            installed = "engine/" + name.removeprefix("source/")
            require(observed.get(installed, {}).get("sha256") == expected_hash,
                    "Source archive installed overlay differs: " + installed)
    for grammar in lock.get("grammars", []):
        for name, expected_hash in grammar["generated_files"].items():
            relative = "include/" + name if PurePosixPath(name).suffix == ".h" else name
            installed = "engine/languages/native_scripts/" + grammar["language"] + "/" + relative
            require(observed.get(installed, {}).get("sha256") == expected_hash,
                    "Source archive generated grammar differs: " + installed)


def archive_license(directory, lock, lock_hash):
    observed, selected = source_archive_members(directory / "opengrep-source.tar.gz")
    require(selected["inputs/source-lock.json"] == (directory / "source-lock.json").read_bytes(),
            "Source archive lock differs from artifact")
    manifest = json.loads(selected["SOURCE-MANIFEST.json"], object_pairs_hook=unique_object)
    require(isinstance(manifest, dict) and set(manifest) == {"identity", "files"}
            and isinstance(manifest["files"], dict), "Invalid source manifest schema")
    for record in manifest["files"].values():
        require(isinstance(record, dict) and ((set(record) == {"symlink"} and isinstance(record["symlink"], str))
                or (set(record) == {"bytes", "sha256"} and type(record["bytes"]) is int
                    and record["bytes"] >= 0 and isinstance(record["sha256"], str))), "Invalid source manifest member schema")
    require(manifest.get("identity") == {"base_revision": lock["revision"], "interfaces_revision": lock["interfaces_revision"],
                                         "source_lock_sha256": lock_hash}, "Source archive identity differs")
    require(manifest.get("files") == observed, "Source archive members differ from source manifest")
    validate_archived_inputs(observed, lock, lock_hash)
    license_bytes = selected["engine/LICENSE"]
    if (directory / "LICENSE").exists():
        require(regular(directory / "LICENSE").read_bytes() == license_bytes, "Artifact license differs from source archive")
    return license_bytes


def deployment_version(parts):
    require(isinstance(parts, list) and 1 <= len(parts) <= 3
            and all(type(part) is int and part >= 0 for part in parts), "Invalid platform deployment version")
    return tuple(parts + [0] * (3 - len(parts)))


def validate_platform(directory, package, target, binary_hash):
    system, arch = target
    checks = read_json(directory / "platform-checks.json")
    runtime = read_json(directory / "runtime.json")
    if system == "darwin":
        minimum = read_json(package / "locks/runtimes.json")["macos"]["deployment_target"]
        require(checks.get("deployment_target") == minimum
                and runtime.get("environment", {}).get("MACOSX_DEPLOYMENT_TARGET") == minimum,
                "Runtime deployment target differs from lock")
        ceiling = deployment_version([int(part) for part in minimum.split(".")])
        images, seen = checks.get("images"), set()
        require(isinstance(images, list) and images, "Platform image checks missing")
        for image in images:
            name = image["path"]
            path = PurePosixPath(name)
            require(not path.is_absolute() and ".." not in path.parts and name not in seen, "Invalid platform image path")
            seen.add(name)
            machine = "x86_64" if arch == "amd64" else arch
            require(machine in image.get("architectures", []), f"Platform architecture mismatch: {name}")
            versions = image.get("deployment_versions")
            require(isinstance(versions, list) and versions
                    and all(deployment_version(v) <= ceiling for v in versions), f"Platform minimum OS mismatch: {name}")
            for value in image.get("dependencies", []) + image.get("rpaths", []):
                require(isinstance(value, str) and value and ".." not in PurePosixPath(value).parts
                        and (not value.startswith("/") or value.startswith(("/usr/lib/", "/System/Library/"))),
                        f"Platform uses non-system absolute dependency: {name}")
            if name == "opengrep":
                require(image.get("sha256") == binary_hash, "Platform checks bind a different executable")
        require("opengrep" in seen, "Platform executable check missing")
    else:
        raise ValueError("No maintained platform qualification validator for " + system)


def validate_artifact(directory, package, lock, target, *, require_license=True, profile=None, inspect=None):
    artifact_tree(directory)
    lock_hash = digest(package / "source-lock.json")
    require((directory / "source-lock.json").read_bytes() == (package / "source-lock.json").read_bytes(),
            "Artifact source lock differs from checked-in source")
    provenance = read_json(directory / "provenance.json")
    version = f'{lock["upstream_version"]}+paintedwolf.{lock["patch_version"]}'
    architecture = {"x86_64": "amd64", "aarch64": "arm64"}.get(provenance.get("architecture"), provenance.get("architecture"))
    identity = {"schema_version": 1, "version": version, "upstream_revision": lock["revision"],
                "source_lock_sha256": lock_hash, "platform": target[0], "architecture": target[1]}
    for field, expected in identity.items():
        actual = architecture if field == "architecture" else provenance.get(field)
        require(actual == expected,
                f"Artifact provenance identity differs: {field}: expected {expected!r}, got {actual!r}")
    for name, key in (("opengrep", "binary"), ("opengrep-source.tar.gz", "source_archive"),
                      ("contracts.jsonl", "contracts"), ("platform-checks.json", "platform_checks"), ("runtime.json", "runtime")):
        path = directory / name
        require(digest(path) == provenance.get(key + "_sha256"), f"Artifact digest mismatch: {name}")
        if key in ("binary", "source_archive"):
            require(type(provenance.get(key + "_bytes")) is int and path.stat().st_size == provenance[key + "_bytes"],
                    f"Artifact size mismatch: {name}")
    require(os.access(directory / "opengrep", os.X_OK), "Artifact executable is not executable")
    signing = signing_module()
    profile = profile or signing.SigningProfile.parse(None, platform=target[0])
    signing.validate_signing_record(provenance.get("signing"), profile,
                                    provenance["binary_sha256"], provenance["binary_bytes"])
    if profile.record()["mode"] == "developer-id":
        require(inspect is not None, "Developer ID artifact requires native signature validation")
        require(inspect(directory / "opengrep") == provenance["signing"]["outer"],
                "Native executable signature differs from build record")
    validate_contracts(directory / "contracts.jsonl", expected_contracts(package))
    validate_platform(directory, package, target, provenance["binary_sha256"])
    license_bytes = archive_license(directory, lock, lock_hash)
    if require_license:
        regular(directory / "LICENSE")
    return license_bytes


@contextmanager
def cache_lock(path):
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode), "Cache lock is not a regular file")
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def build_artifact(package, root, jobs, profile):
    require(profile["mode"] == "adhoc", "Source compilation is ad-hoc; use isolated native release stages for Developer ID artifacts")
    command = [sys.executable, str(package / "build.py"), str(root), "--jobs", str(jobs)]
    with (root.parent / "build.log").open("wb") as log:
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as process:
            for block in iter(lambda: process.stdout.read1(65536), b""):
                log.write(block)
                log.flush()
                sys.stderr.write(block.decode("utf-8", errors="replace"))
                sys.stderr.flush()
            require(process.wait() == 0, f"Source build failed; inspect {log.name}")
    return root / "artifact"


def write_failure(path, key, build, error):
    with tempfile.NamedTemporaryFile(mode="w", prefix=".failure-", dir=path.parent, delete=False) as output:
        temporary = Path(output.name)
        try:
            json.dump({"key": key, "build_directory": str(build), "diagnostic": str(error)}, output)
            output.flush()
            os.fsync(output.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def publish(source, destination, cache, package, lock, target, profile, inspect):
    validate_artifact(source, package, lock, target, require_license=False, profile=profile, inspect=inspect)
    with tempfile.TemporaryDirectory(prefix=".install-", dir=cache) as install:
        staging = Path(install) / "artifact"
        shutil.copytree(source, staging, symlinks=True)
        license_bytes = validate_artifact(staging, package, lock, target, require_license=False, profile=profile, inspect=inspect)
        (staging / "LICENSE").write_bytes(license_bytes)
        validate_artifact(staging, package, lock, target, profile=profile, inspect=inspect)
        for path in staging.rglob("*"):
            if path.is_file():
                with path.open("rb") as stream:
                    os.fsync(stream.fileno())
        os.replace(staging, destination)
        descriptor = os.open(cache, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def resolve(package, cache, seed=None, jobs=2, no_build=False, builder=build_artifact, target=None,
            retry_failed=False, signing_profile=None):
    require(type(jobs) is int and 1 <= jobs <= 16, "Build jobs must be between 1 and 16")
    target = target or native_target()
    signing = signing_module()
    profile = signing.SigningProfile.parse(signing_profile, platform=target[0])
    with tempfile.TemporaryDirectory(prefix="opengrep-artifact-inputs-") as temporary:
        frozen = Path(temporary) / "inputs"
        lock = snapshot_inputs(package, frozen)
        system, arch = target
        lock_system = "macos" if system == "darwin" else system
        require((frozen / f"locks/{lock_system}-{arch}.opam.export").is_file(), "Native platform has no maintained dependency lock")
        key = artifact_cache_key(digest(frozen / "source-lock.json"), target, profile)
        inspector = Path(temporary) / "signing-inspector"
        def inspect(binary):
            if not inspector.exists():
                signing.compile_inspector(inspector)
            return signing.inspect_image(inspector, binary, profile)
        require(not cache.is_symlink(), "Cache directory is a symlink")
        cache.mkdir(parents=True, exist_ok=True)
        cache = cache.resolve(strict=True)
        destination, failure = cache / key, cache / (key + ".failed.json")
        with cache_lock(cache / (key + ".lock")):
            if destination.exists() or destination.is_symlink():
                validate_artifact(destination, frozen, lock, target, profile=profile, inspect=inspect)
                failure.unlink(missing_ok=True)
                return destination
            if failure.exists() or failure.is_symlink():
                previous = read_json(failure)
                require(previous.get("key") == key, "Failed build marker identity differs")
                require(seed is not None or retry_failed,
                        f"Previous source build failed: {previous.get('diagnostic')}; "
                        "use --retry-failed or --seed to recover explicitly")
            require(seed is not None or not no_build, "No qualified artifact is cached; seed an artifact or allow a source build")
            if seed is not None:
                publish(seed, destination, cache, frozen, lock, target, profile, inspect)
            else:
                # The Python framework has bounded Mach-O install-name space.
                # Keep its temporary linker identity independent of checkout depth.
                build = Path(tempfile.mkdtemp(prefix="pwog-", dir="/tmp" if target[0] == "darwin" else None))
                try:
                    # Directory-selection contracts must not inherit build/ ignore patterns.
                    source = builder(frozen, build / "work", jobs, profile.record())
                    publish(source, destination, cache, frozen, lock, target, profile, inspect)
                except BaseException as error:
                    write_failure(failure, key, build, error)
                    raise
                shutil.rmtree(build)
            failure.unlink(missing_ok=True)
            return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path,
                        default=os.environ.get("OPENGREP_CACHE_DIR") or PACKAGE.parent / ".cache/artifacts")
    parser.add_argument("--seed", type=Path)
    parser.add_argument("--jobs", type=int, choices=range(1, 17), default=2)
    parser.add_argument("--no-build", action="store_true")
    parser.add_argument("--retry-failed", action="store_true", help="Explicitly retry a failed source build")
    parser.add_argument("--signing-profile", type=Path, default=os.environ.get("OPENGREP_SIGNING_PROFILE") or None)
    args = parser.parse_args()
    try:
        profile = read_json(args.signing_profile) if args.signing_profile else None
        result = resolve(PACKAGE, args.cache_dir, args.seed, args.jobs, args.no_build,
                         retry_failed=args.retry_failed, signing_profile=profile)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.CalledProcessError, tarfile.TarError) as error:
        print("Opengrep artifact: " + str(error), file=sys.stderr)
        return 1
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
