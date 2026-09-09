#!/usr/bin/env python3
"""Materialize pinned build runtimes without using host-installed native libraries."""
import argparse
import hashlib
import json
import os
import platform
import re
from pathlib import Path
import shutil
import subprocess
import tempfile

MACHO_MAGIC = {bytes.fromhex(value) for value in (
    "feedface", "cefaedfe", "feedfacf", "cffaedfe", "cafebabe", "bebafeca", "cafebabf", "bfbafeca",
)}
FRAMEWORK_PREFIX = "/Library/Frameworks/Python.framework/"


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def run(args, cwd=None, env=None):
    subprocess.run(args, cwd=cwd, env=env, check=True)


def download(spec, destination):
    if not destination.exists():
        temporary = destination.with_suffix(".download")
        run(["curl", "--fail", "--location", "--silent", "--show-error", "--connect-timeout", "20",
             "--max-time", "180", "--retry", "2", "--output", str(temporary), spec["url"]])
        if digest(temporary) != spec["sha256"]:
            raise RuntimeError("Downloaded runtime archive does not match its digest: " + spec["url"])
        temporary.replace(destination)
    if digest(destination) != spec["sha256"]:
        raise RuntimeError("Cached runtime archive does not match its digest: " + str(destination))


def native_libraries(root, spec, jobs):
    prefix = root / "prefix"
    target = spec["deployment_target"]
    flags = "-O2 -mmacosx-version-min=" + target
    env = dict(os.environ, MACOSX_DEPLOYMENT_TARGET=target, CFLAGS=flags, CXXFLAGS=flags,
               LDFLAGS="-mmacosx-version-min=" + target)
    records = []
    for library in spec["native_libraries"]:
        name = library["name"] + "-" + library["version"]
        archive = root / (name + ".archive")
        download(library, archive)
        source = root / name
        source.mkdir()
        run(["tar", "-xf", str(archive), "--strip-components=1", "-C", str(source)])
        if library["name"] == "zstd":
            commands = [["make", "-C", "lib", "-j" + str(jobs), "libzstd.a"],
                        ["make", "-C", "lib", "PREFIX=" + str(prefix), "install-static", "install-includes", "install-pc"]]
        else:
            commands = [["./configure", "--prefix=" + str(prefix), *library["configure"]],
                        ["make", "-j" + str(jobs)], ["make", "install"]]
        for command in commands:
            run(command, source, env)
        records.append({"name": library["name"], "version": library["version"],
                        "source_sha256": library["sha256"], "commands": commands})
    archives = {path.name: digest(path) for path in sorted((prefix / "lib").glob("*.a"))}
    return prefix, {"libraries": records, "archives": archives, "deployment_target": target}


def relocate_framework(framework):
    framework = framework.resolve()
    records = []
    for path in sorted(framework.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        with path.open("rb") as source:
            if source.read(4) not in MACHO_MAGIC:
                continue
        before = digest(path)
        dependencies = subprocess.check_output(["otool", "-L", str(path)], text=True)
        changes = {}
        for line in dependencies.splitlines():
            dependency = line.strip().split(" (", 1)[0]
            if dependency.startswith(FRAMEWORK_PREFIX):
                target = framework / dependency[len(FRAMEWORK_PREFIX):]
                if not target.exists():
                    raise RuntimeError("Python framework dependency is absent: " + dependency)
                changes[dependency] = "@loader_path/" + os.path.relpath(target, path.parent)
        identities = subprocess.check_output(["otool", "-D", str(path)], text=True)
        arguments = [item for old, new in changes.items() for item in ("-change", old, new)]
        if any(line.startswith(FRAMEWORK_PREFIX) for line in identities.splitlines()):
            # Python's linker identity must resolve when Nuitka links its executable.
            # Other library identities are metadata, not dependency search paths.
            arguments.extend(["-id", str(path) if path.name == "Python" else path.name])
        if not arguments:
            continue
        path.chmod(path.stat().st_mode | 0o200)
        run(["install_name_tool", *arguments, str(path)])
        # Sign the Mach-O itself; nested Tcl frameworks also contain unsigned scripts.
        with tempfile.TemporaryDirectory(prefix="opengrep-python-sign-") as temporary:
            image = Path(temporary) / "image"
            shutil.copy2(path, image)
            run(["codesign", "--force", "--sign", "-", str(image)])
            shutil.copy2(image, path)
        records.append({"path": path.relative_to(framework).as_posix(),
                        "before_sha256": before, "after_sha256": digest(path)})
    return records


def python_runtime(root, spec):
    archive = root / ("python-" + spec["version"] + ".pkg")
    download(spec, archive)
    run(["pkgutil", "--check-signature", str(archive)])
    expanded = root / "python-package"
    run(["pkgutil", "--expand-full", str(archive), str(expanded)])
    framework = root / "Python.framework"
    shutil.copytree(expanded / "Python_Framework.pkg/Payload", framework, symlinks=True)
    records = relocate_framework(framework)
    python = framework / "Versions" / spec["series"] / "bin" / ("python" + spec["series"])
    run([str(python), "-c", "import ssl,sys; assert '.'.join(map(str,sys.version_info[:3])) == " + repr(spec["version"])])
    return python, {"version": spec["version"], "installer_sha256": spec["sha256"], "relocated_files": records}


def tree_sitter(root, spec):
    run(["./configure"], root)
    downloads = root / "downloads"
    downloads.mkdir(exist_ok=True)
    archive = downloads / ("v" + spec["version"] + ".tar.gz")
    download(spec, archive)
    run(["tar", "-xf", str(archive)], downloads)
    name = "tree-sitter-" + spec["version"]
    run(["patch", "--backup", name + "/Makefile", "../patch/" + name + "/Makefile.patch"], downloads)
    run(["./scripts/install-tree-sitter-lib"], root)


def deployment_versions(load_commands):
    versions, command = [], None
    for line in load_commands.splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[0] == "cmd":
            command = fields[1]
        elif len(fields) == 2 and ((command == "LC_BUILD_VERSION" and fields[0] == "minos")
                                  or (command == "LC_VERSION_MIN_MACOSX" and fields[0] == "version")):
            if not re.fullmatch(r"\d+\.\d+(?:\.\d+)?", fields[1]):
                raise RuntimeError("Malformed Mach-O deployment version")
            versions.append(tuple(int(part) for part in fields[1].split(".")))
            command = None
    return versions


def linked_libraries(load_commands):
    dependencies, rpaths, command = [], [], None
    loads = {"LC_LOAD_DYLIB", "LC_LOAD_WEAK_DYLIB", "LC_REEXPORT_DYLIB", "LC_LAZY_LOAD_DYLIB", "LC_LOAD_UPWARD_DYLIB"}
    for line in load_commands.splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[0] == "cmd":
            command = fields[1]
            continue
        match = re.fullmatch(r"\s*(name|path) (.+) \(offset \d+\)", line)
        if match and command in loads and match[1] == "name":
            dependencies.append(match[2])
        elif match and command == "LC_RPATH" and match[1] == "path":
            rpaths.append(match[2])
    return list(dict.fromkeys(dependencies)), list(dict.fromkeys(rpaths))


def system_library(value):
    return os.path.normpath(value).startswith(("/usr/lib/", "/System/Library/"))


def validate_relative_dependencies(path, distribution, dependencies, rpaths):
    def expand(value):
        for marker, directory in (("@loader_path/", path.parent),
                                  ("@executable_path/", distribution)):
            if value.startswith(marker):
                return directory / value[len(marker):]
        if value.startswith("/"):
            return Path(value)
        return None

    for dependency in dependencies:
        if system_library(dependency):
            continue
        if not path.is_relative_to(distribution):
            raise RuntimeError("Onefile launcher has an external runtime dependency: " + dependency)
        if dependency.startswith("@rpath/"):
            candidates = [directory / dependency[len("@rpath/"):] for value in rpaths
                          if (directory := expand(value + "/")) is not None]
        else:
            candidate = expand(dependency)
            candidates = [] if candidate is None else [candidate]
        if not candidates or not any(candidate.resolve().is_relative_to(distribution.resolve())
                                     and candidate.is_file() for candidate in candidates):
            raise RuntimeError("Packaged dependency is missing or outside the distribution: " + dependency)


def validate_macos(root, target):
    distribution = root / "entrypoint.dist"
    if not distribution.is_dir():
        raise RuntimeError("Nuitka standalone distribution is missing")
    maximum = tuple(int(part) for part in target.split("."))
    architecture = platform.machine()
    records = []
    for path in [root / "opengrep", *sorted(distribution.rglob("*"))]:
        if path.is_symlink() or not path.is_file():
            continue
        with path.open("rb") as source:
            if source.read(4) not in MACHO_MAGIC:
                continue
        commands = subprocess.check_output(["otool", "-l", str(path)], text=True)
        architectures = subprocess.check_output(["lipo", "-archs", str(path)], text=True).split()
        if architecture not in architectures:
            raise RuntimeError("Packaged Mach-O lacks the target architecture: " + str(path))
        versions = deployment_versions(commands)
        if not versions or any(version + (0,) * (3-len(version)) > maximum + (0,) * (3-len(maximum)) for version in versions):
            raise RuntimeError("Mach-O deployment target exceeds the release baseline: " + str(path))
        dependencies, rpaths = linked_libraries(commands)
        for dependency in dependencies + rpaths:
            if dependency.startswith("/") and not system_library(dependency):
                raise RuntimeError("Packaged Mach-O depends on a build-host path: " + dependency)
        validate_relative_dependencies(path, distribution, dependencies, rpaths)
        records.append({"path": path.relative_to(root).as_posix(), "sha256": digest(path),
                        "architectures": architectures, "deployment_versions": versions,
                        "dependencies": dependencies, "rpaths": rpaths})
    if not records:
        raise RuntimeError("No Mach-O artifacts were found")
    (root / "platform-checks.json").write_text(json.dumps({"deployment_target": target, "images": records}, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("macos", "tree-sitter", "validate-macos"))
    parser.add_argument("root", type=Path)
    parser.add_argument("lock", type=Path)
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    if not 1 <= args.jobs <= 16:
        parser.error("jobs must be between 1 and 16")
    root = args.root.resolve()
    lock = json.loads(args.lock.read_text())
    if args.mode == "validate-macos":
        validate_macos(root, lock["macos"]["deployment_target"])
        return
    if args.mode == "tree-sitter":
        tree_sitter(root, lock["tree_sitter"])
        return
    root.mkdir()
    spec = lock["macos"]
    prefix, native = native_libraries(root, spec, args.jobs)
    python, runtime = python_runtime(root, spec["python"])
    target = spec["deployment_target"]
    env = {"MACOSX_DEPLOYMENT_TARGET": target,
           "CFLAGS": "-O2 -mmacosx-version-min=" + target,
           "CXXFLAGS": "-O2 -mmacosx-version-min=" + target,
           "CPPFLAGS": "-I" + str(prefix / "include"),
           "LDFLAGS": "-L" + str(prefix / "lib"),
           "PKG_CONFIG_PATH": str(prefix / "lib/pkgconfig"),
           "PKG_CONFIG_LIBDIR": str(prefix / "lib/pkgconfig"),
           "LIBRARY_PATH": str(prefix / "lib"), "C_INCLUDE_PATH": str(prefix / "include"),
           "SEMGREP_LIBEV_ARCHIVE_PATH": str(prefix / "lib/libev.a")}
    (root / "runtime.json").write_text(json.dumps({"python": str(python), "environment": env,
                                                  "native": native, "python_runtime": runtime}, indent=2) + "\n")


if __name__ == "__main__":
    main()
