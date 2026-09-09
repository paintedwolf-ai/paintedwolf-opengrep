#!/usr/bin/env python3
"""Materialize and build the reviewed Opengrep source package in an isolated directory."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import uuid


PACKAGE = Path(__file__).resolve().parent


def dependency_support(package):
    spec = importlib.util.spec_from_file_location("opengrep_build_dependencies", package / "build_support/dependencies.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(args, cwd, env=None):
    subprocess.run(args, cwd=cwd, env=env, check=True)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def engine_version(lock):
    upstream, revision = lock["upstream_version"], lock["patch_version"]
    if (not isinstance(upstream, str)
            or re.fullmatch(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", upstream) is None
            or type(revision) is not int or revision < 1):
        raise RuntimeError("Invalid locked engine version")
    return f"{upstream}+paintedwolf.{revision}"


def stamp_version(source, lock):
    version = engine_version(lock)
    declarations = (
        ("cli/setup.py", r'^([ \t]*version=")([^"\n]*)(",[ \t]*)$'),
        ("cli/src/semgrep/__init__.py", r'^(__VERSION__ = ")([^"\n]*)("[ \t]*)$'),
        ("src/core/Version.ml", r'^(let version = ")([^"\n]*)("[ \t]*)$'),
    )
    replacements = []
    for relative, expression in declarations:
        path = source / relative
        text = path.read_text()
        matches = list(re.finditer(expression, text, re.MULTILINE))
        if len(matches) != 1 or matches[0][2] != lock["upstream_version"]:
            raise RuntimeError(f"Unexpected upstream version declaration: {relative}")
        match = matches[0]
        replacements.append((path, text[:match.start(2)] + version + text[match.end(2):]))
    for path, text in replacements:
        path.write_text(text)


def validate_reported_version(reported, lock):
    expected = engine_version(lock)
    if reported != expected:
        raise RuntimeError(f"Built engine version mismatch: expected {expected}, reported {reported!r}")


def patch_series(package):
    manifest = json.loads((package / "patches/series.json").read_text())
    if manifest.get("format") != 1 or not manifest.get("patches"):
        raise RuntimeError("Patch series has no supported ordered manifest")
    seen, paths, result = set(), set(), []
    for entry in manifest["patches"]:
        name, target, relative = entry["id"], entry["target"], entry["patch"]
        path = PurePosixPath(relative)
        if (not name or name in seen or target not in ("engine", "interfaces")
                or path.is_absolute() or ".." in path.parts
                or path.parent != PurePosixPath("patches/series") or path.suffix != ".patch"
                or relative in paths or not (package / relative).is_file()):
            raise RuntimeError("Invalid or duplicate patch series entry: " + str(name))
        if any(dependency not in seen for dependency in entry["requires"]):
            raise RuntimeError("Patch dependency must precede its consumer: " + name)
        seen.add(name)
        paths.add(relative)
        result.append((target, package / relative))
    actual = {path.relative_to(package).as_posix()
              for path in (package / "patches/series").glob("*.patch")}
    if paths != actual:
        raise RuntimeError("Patch series contains unlisted patches")
    return result


def checkout(url, revision, path):
    run(["git", "init", str(path)], path.parent)
    run(["git", "remote", "add", "origin", url], path)
    run(["git", "fetch", "--depth", "1", "origin", revision], path)
    run(["git", "checkout", "--detach", "FETCH_HEAD"], path)
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()
    if actual != revision:
        raise RuntimeError("Fetched source does not match its revision lock")


def snapshot_package(package, destination):
    for relative in ("source-lock.json", "build.py", "verify.py", "patches", "source", "locks", "build_support",
                     "signing", "signing/signing.py", "signing/native_signatures.m", "signing/release-profile.json"):
        if (package / relative).is_symlink():
            raise RuntimeError(f"Source package contains a symlink: {relative}")
    lock_bytes = (package / "source-lock.json").read_bytes()
    lock = json.loads(lock_bytes)
    inputs = [path for path in (package / "build.py", package / "verify.py",
                               package / "signing/signing.py", package / "signing/native_signatures.m",
                               package / "signing/release-profile.json") if path.is_file()]
    for folder in ("patches", "source", "locks", "build_support"):
        for path in (package / folder).rglob("*"):
            if path.is_symlink():
                raise RuntimeError(f"Source package contains a symlink: {path.relative_to(package)}")
            if folder == "build_support" and "__pycache__" in path.relative_to(package / folder).parts:
                continue
            if path.is_file():
                inputs.append(path)
    actual = {path.relative_to(package).as_posix() for path in inputs}
    expected = set(lock["files"])
    if actual != expected:
        raise RuntimeError(f"Source package inventory mismatch: unlocked={sorted(actual - expected)}, missing={sorted(expected - actual)}")
    destination.mkdir()
    for relative in sorted(expected):
        path = package / relative
        if path.is_symlink():
            raise RuntimeError(f"Source package contains a symlink: {relative}")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != lock["files"][relative]:
            raise RuntimeError(f"Source package integrity mismatch: {relative}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    (destination / "source-lock.json").write_bytes(lock_bytes)
    patch_series(destination)
    return lock


def prepare(root, package, lock):
    dependencies = dependency_support(package)
    source = root / "engine"
    checkout(lock["upstream"], lock["revision"], source)
    run(["git", "submodule", "update", "--init", "--recursive", "--jobs", "2"], source)
    interfaces = source / "cli/src/semgrep/semgrep_interfaces"
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=interfaces, text=True).strip()
    if actual != lock["interfaces_revision"]:
        raise RuntimeError("Interface submodule differs from lock")
    for target, patch in patch_series(package):
        run(["git", "apply", str(patch)], source if target == "engine" else interfaces)
    shutil.copytree(package / "source", source, dirs_exist_ok=True)
    stamp_version(source, lock)
    native = source / "languages/native_scripts"
    for grammar in lock["grammars"]:
        name = grammar["language"]
        path = root / ("grammar-" + name)
        checkout(grammar["upstream"], grammar["revision"], path)
        patch = grammar_patch(package, grammar)
        if patch is not None:
            run(["git", "apply", str(patch)], path)
        system = {"Darwin": "macos", "Linux": "linux"}.get(platform.system())
        architecture = {"aarch64": "arm64", "x86_64": "amd64"}.get(platform.machine(), platform.machine())
        generator = dependencies.grammar_generator(package, root / "generators", grammar["generator"], f"{system}-{architecture}")
        run([str(generator), "generate", "--abi", str(grammar["abi"])], path)
        for relative, expected in grammar["generated_files"].items():
            relative_path = PurePosixPath(relative)
            if relative_path.is_absolute() or ".." in relative_path.parts:
                raise RuntimeError("Invalid grammar output path: " + relative)
            generated = path / "src" / relative
            if digest(generated) != expected:
                raise RuntimeError("Grammar output differs from lock: " + name + "/" + relative)
            output = Path("include") / relative if relative_path.suffix == ".h" else Path(relative)
            destination = native / name / output
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(generated, destination)
    return source


def grammar_patch(package, grammar):
    relative = grammar["patch"]
    if relative is None:
        return None
    path = PurePosixPath(relative)
    if (path.parent != PurePosixPath("patches") or path.suffix != ".patch"
            or not (package / path).is_file()):
        raise RuntimeError("Invalid grammar patch path: " + relative)
    return package / path


def build(root, package, source, lock, jobs, python, signing, profile):
    if profile.mode != "adhoc":
        raise RuntimeError("Native compilation requires ad-hoc signing; use the isolated native release stages for Developer ID")
    dependencies = dependency_support(package)
    temporary = root / "tmp"
    temporary.mkdir(mode=0o700, exist_ok=True)
    env = dict(os.environ, OPAMROOT=str(root / "opam"), OPAMJOBS=str(jobs),
               PIP_DISABLE_PIP_VERSION_CHECK="1", TMPDIR=str(temporary.resolve()),
               OPAMREQUIRECHECKSUMS="true", OPAMNOCHECKSUMS="false", OPAMNOSELFUPGRADE="true")
    architecture = {"aarch64": "arm64", "x86_64": "amd64"}.get(platform.machine(), platform.machine())
    system = {"Darwin": "macos", "Linux": "linux", "Windows": "windows"}.get(platform.system())
    dependency_lock = package / "locks" / f"{system}-{architecture}.opam.export"
    if not dependency_lock.exists():
        raise RuntimeError(f"No qualified OCaml dependency lock for {system}/{architecture}")
    dependencies.fetch_python(package, root / "dependencies")
    runtime_driver = package / "build_support/runtime.py"
    runtime_lock = package / "locks/runtimes.json"
    if system == "macos":
        if python is not None:
            raise RuntimeError("macOS builds use the pinned private Python runtime")
        runtime_root = root / "runtime"
        run([sys.executable, str(runtime_driver), "macos", str(runtime_root), str(runtime_lock), "--jobs", str(jobs)], source, env)
        runtime = json.loads((runtime_root / "runtime.json").read_text())
        env.update(runtime["environment"])
        python = runtime["python"]
    else:
        python = python or "python3.13"
    dependencies.initialize_opam(root, source, env)
    run(["opam", "switch", "create", ".", "--empty", "--no-install", "-y"], source, env)
    run(["opam", "switch", "import", str(dependency_lock), "-y", "--assume-depexts"], source, env)
    run([sys.executable, str(runtime_driver), "tree-sitter", str(source / "libs/ocaml-tree-sitter-core"), str(runtime_lock)], source, env)
    # The upstream configure step produces the tree-sitter include/library paths.
    command = '. libs/ocaml-tree-sitter-core/tree-sitter-config.sh; exec opam exec -- dune build -j "$1" _build/install/default/bin/opengrep-core _build/install/default/bin/opengrep-cli _build/install/default/bin/opengrep'
    run(["sh", "-c", command, "opengrep-build", str(jobs)], source, env)
    core = source / "cli/src/semgrep/bin/opengrep-core"
    shutil.copy2(source / "_build/default/src/main/Main.exe", core)
    core.chmod(0o755)
    venv = root / "python"
    run([python, "-m", "venv", str(venv)], source, env)
    py = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    dependencies.install_python(py, package, root / "dependencies", env=env)
    run([str(py), "-I", "-m", "pip", "--isolated", "install", "--no-index", "--no-build-isolation", "--no-deps", "-e", "./cli"], source, env)
    env["PYTHON_BIN"] = str(py)
    env["NUITKA_JOBS"] = str(jobs)
    build_id = "paintedwolf-" + digest(package / "source-lock.json") + "-" + profile.digest() + "-" + uuid.uuid4().hex
    env["OPENGREP_BUILD_ID"] = build_id
    env.pop("OPENGREP_SIGN_IDENTITY", None)
    version = "v" + lock["upstream_version"] + "." + str(lock["patch_version"])
    run(["bash", "scripts/build-nuitka.sh", version, "true", "src/semgrep"], source, env)
    binary = source / "cli" / ("opengrep.exe" if os.name == "nt" else "opengrep")
    env["XDG_CACHE_HOME"] = str(root / "extraction-cache")
    reported_version = subprocess.check_output([str(binary), "--version"], text=True, env=env).strip()
    validate_reported_version(reported_version, lock)
    signing_record = None
    if system == "macos":
        run([sys.executable, str(runtime_driver), "validate-macos", str(source / "cli"), str(runtime_lock)], source, env)
        shutil.copyfile(source / "cli/platform-checks.json", root / "platform-checks.json")
        inspector = signing.compile_inspector(root / "signature-inspector")
        distribution = source / "cli/entrypoint.dist"
        extracted = root / "extraction-cache/opengrep" / build_id
        required = ("opengrep.bin", "semgrep/bin/opengrep-core")
        standalone_images = signing.inspect_inventory(inspector, distribution, profile, required=required)
        extracted_images = signing.inspect_inventory(inspector, extracted, profile, required=required)
        signing_record = {"profile": profile.record(), "profile_sha256": profile.digest(),
                          "outer": signing.inspect_image(inspector, binary, profile),
                          "standalone": standalone_images, "extracted": extracted_images}
        signing.validate_signing_record(signing_record, profile, digest(binary), binary.stat().st_size)
    with (root / "contracts.jsonl").open("w") as report:
        subprocess.run([str(py), str(package / "verify.py"), str(binary)], stdout=report, env=env, check=True)
    if signing_record is not None:
        signing.verify_inventory_unchanged(distribution, standalone_images)
        signing.verify_inventory_unchanged(extracted, extracted_images)
        signing.validate_signing_record(signing_record, profile, digest(binary), binary.stat().st_size)
    return {"binary": binary, "version": reported_version, "signing": signing_record}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, nargs="?")
    parser.add_argument("--check", action="store_true", help="Verify the complete source inventory without building or using the network")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--python", help="Python interpreter for non-macOS builds")
    args = parser.parse_args()
    if args.check:
        if args.directory or args.prepare_only:
            parser.error("--check does not accept a build directory or --prepare-only")
        with tempfile.TemporaryDirectory(prefix="opengrep-source-check-") as temporary:
            snapshot_package(PACKAGE, Path(temporary) / "inputs")
        print("Opengrep source package integrity verified")
        return
    if args.directory is None:
        parser.error("a build directory is required")
    if args.jobs < 1 or args.jobs > 16:
        parser.error("jobs must be between 1 and 16")
    root = args.directory.resolve()
    if root.is_relative_to(PACKAGE):
        parser.error("build directory must be outside the source package")
    if root.exists():
        parser.error("build directory must not already exist")
    root.mkdir(parents=True)
    package = root / "inputs"
    lock = snapshot_package(PACKAGE, package)
    spec = importlib.util.spec_from_file_location("opengrep_build_signing", package / "signing/signing.py")
    signing = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = signing
    spec.loader.exec_module(signing)
    profile = signing.SigningProfile.parse(None)
    source = prepare(root, package, lock)
    retained = root / "third-party"
    run([sys.executable, str(package / "build_support/corresponding_source.py"), str(retained),
         "--lock", str(package / "locks/corresponding-source.json")], root)
    source_archive = root / "opengrep-source.tar.gz"
    run([sys.executable, str(package / "build_support/source_archive.py"),
         str(root), str(package), str(source_archive), "--retained", str(retained)], root)
    if args.prepare_only:
        print(source)
        return
    built = build(root, package, source, lock, args.jobs, args.python, signing, profile)
    binary = built["binary"]
    output = root / "artifact"
    output.mkdir()
    shutil.copy2(binary, output / binary.name)
    manifest = {"schema_version": 1, "upstream_revision": lock["revision"],
                "source_lock_sha256": digest(package / "source-lock.json"),
                "platform": platform.system().lower(), "architecture": platform.machine(),
                "binary_sha256": digest(binary), "binary_bytes": binary.stat().st_size,
                "contracts_sha256": digest(root / "contracts.jsonl"),
                "source_archive_sha256": digest(source_archive),
                "source_archive_bytes": source_archive.stat().st_size,
                "version": built["version"], "signing": built["signing"]}
    if (root / "platform-checks.json").exists():
        manifest["platform_checks_sha256"] = digest(root / "platform-checks.json")
        shutil.copyfile(root / "platform-checks.json", output / "platform-checks.json")
    if (root / "runtime/runtime.json").exists():
        manifest["runtime_sha256"] = digest(root / "runtime/runtime.json")
    (output / "provenance.json").write_text(json.dumps(manifest, indent=2) + "\n")
    shutil.copyfile(package / "source-lock.json", output / "source-lock.json")
    shutil.copyfile(root / "contracts.jsonl", output / "contracts.jsonl")
    shutil.copyfile(source_archive, output / source_archive.name)
    if (root / "runtime/runtime.json").exists():
        shutil.copyfile(root / "runtime/runtime.json", output / "runtime.json")
    print(output)


if __name__ == "__main__":
    main()
