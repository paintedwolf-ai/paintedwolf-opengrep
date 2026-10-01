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
import struct
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
    """Build the pinned native libraries statically under root/prefix. A macOS spec names
    a deployment target the compiler flags carry; a Linux spec builds with plain -O2."""
    prefix = root / "prefix"
    target = spec.get("deployment_target")
    if target:
        flags = "-O2 -mmacosx-version-min=" + target
        env = dict(os.environ, MACOSX_DEPLOYMENT_TARGET=target, CFLAGS=flags, CXXFLAGS=flags,
                   LDFLAGS="-mmacosx-version-min=" + target)
    else:
        env = dict(os.environ, CFLAGS="-O2 -fPIC", CXXFLAGS="-O2 -fPIC")
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
            # The interpreter library needs an absolute linker identity.
            arguments.extend(["-id", str(path) if path.name == "Python" else path.name])
        if not arguments:
            continue
        path.chmod(path.stat().st_mode | 0o200)
        run(["install_name_tool", *arguments, str(path)])
        # Sign each native image without treating its surrounding files as a bundle.
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
    if platform.system() == "Linux":
        # Without the shared objects the linker takes the archive, so the engine
        # carries tree-sitter instead of depending on the build tree.
        for shared in (root / "tree-sitter/lib").glob("libtree-sitter.so*"):
            shared.unlink()


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



ELF_MAGIC = b"\x7fELF"
ELF_MACHINES = {62: "amd64", 183: "arm64"}
SHT_DYNAMIC = 6
SHT_GNU_VERNEED = 0x6FFFFFFE
DT_NEEDED, DT_RPATH, DT_RUNPATH = 1, 15, 29


def is_elf_image(path):
    with open(path, "rb") as source:
        return source.read(4) == ELF_MAGIC


def _elf_string(data, offset):
    end = data.index(b"\0", offset)
    return data[offset:end].decode()


def read_elf(path):
    """What a little-endian ELF64 image needs at load time: its architecture, the shared
    libraries it names, its runtime search paths, and the glibc symbol versions it requires."""
    with open(path, "rb") as source:
        data = source.read()
    if data[:4] != ELF_MAGIC or data[4] != 2 or data[5] != 1:
        raise ValueError("Not a little-endian ELF64 image: " + str(path))
    machine = struct.unpack_from("<H", data, 18)[0]
    if machine not in ELF_MACHINES:
        raise ValueError("Unsupported ELF machine %d: %s" % (machine, path))
    shoff = struct.unpack_from("<Q", data, 0x28)[0]
    shentsize, shnum = struct.unpack_from("<HH", data, 0x3A)
    sections = [struct.unpack_from("<IIQQQQIIQQ", data, shoff + index * shentsize) for index in range(shnum)]
    dependencies, rpaths, versions = [], [], set()
    for _name, kind, _flags, _address, offset, size, link, info, _align, entsize in sections:
        if kind == SHT_DYNAMIC:
            strings = sections[link][4]
            for position in range(offset, offset + size, entsize or 16):
                tag, value = struct.unpack_from("<qQ", data, position)
                if tag == 0:
                    break
                if tag == DT_NEEDED:
                    dependencies.append(_elf_string(data, strings + value))
                elif tag in (DT_RPATH, DT_RUNPATH):
                    rpaths.extend(part for part in _elf_string(data, strings + value).split(":") if part)
        elif kind == SHT_GNU_VERNEED:
            strings = sections[link][4]
            position = offset
            for _ in range(info):
                _version, count, _file, aux, following = struct.unpack_from("<HHIII", data, position)
                entry = position + aux
                for _ in range(count):
                    _hash, _vflags, _other, name, following_aux = struct.unpack_from("<IHHII", data, entry)
                    label = _elf_string(data, strings + name)
                    if label.startswith("GLIBC_") and label[6:7].isdigit():
                        versions.add(label[6:])
                    entry += following_aux
                position += following
    order = lambda value: tuple(int(part) for part in value.split("."))  # noqa: E731
    return {"architecture": ELF_MACHINES[machine], "dependencies": list(dict.fromkeys(dependencies)),
            "rpaths": list(dict.fromkeys(rpaths)), "glibc_versions": sorted(versions, key=order)}


# The libraries a Linux image may take from the host: glibc and the loader, and
# libgcc_s, which glibc itself loads for thread cancellation and unwinding, so
# every glibc system carries it (as manylinux also assumes).
LINUX_SYSTEM_LIBRARIES = {"libc.so.6", "libm.so.6", "libdl.so.2", "libpthread.so.0", "librt.so.1",
                          "libutil.so.1", "libresolv.so.2", "ld-linux-x86-64.so.2", "ld-linux-aarch64.so.1",
                          "libgcc_s.so.1"}
LINUX_ARCHITECTURES = {"x86_64": "amd64", "aarch64": "arm64"}


def static_cxx_runtime(prefix):
    """The compiler's libstdc++ archive in the prefix, which the linker searches before
    the system directories, so C++ code links it statically."""
    archive = Path(subprocess.check_output(["g++", "-print-file-name=libstdc++.a"], text=True).strip())
    if not archive.is_absolute() or not archive.is_file():
        raise RuntimeError("The C++ compiler has no static libstdc++")
    shutil.copy2(archive, prefix / "lib/libstdc++.a")
    return {"libstdc++": {"archive": str(archive), "sha256": digest(archive)}}


def python_from_source(root, spec, prefix, jobs):
    """CPython built from its pinned source tarball, with zlib from the prefix linked
    statically and expat and libmpdec from CPython's own tree."""
    archive = root / ("Python-" + spec["version"] + ".tar.xz")
    download(spec, archive)
    source = root / "python-source"
    source.mkdir()
    run(["tar", "-xf", str(archive), "--strip-components=1", "-C", str(source)])
    install = root / "python"
    env = dict(os.environ, CFLAGS="-O2", CPPFLAGS="-I" + str(prefix / "include"), LDFLAGS="-L" + str(prefix / "lib"),
               ZLIB_CFLAGS="-I" + str(prefix / "include"), ZLIB_LIBS=str(prefix / "lib/libz.a"))
    run(["./configure", "--prefix=" + str(install), *spec["configure"]], source, env)
    run(["make", "-j" + str(jobs)], source, env)
    run(["make", "install"], source, env)
    python = install / "bin" / ("python" + spec["series"])
    run([str(python), "-c", "import sys, ssl, zlib, pyexpat, lzma, bz2, ctypes, sqlite3; "
         "assert '.'.join(map(str, sys.version_info[:3])) == " + repr(spec["version"])])
    return python, {"version": spec["version"], "series": spec["series"], "url": spec["url"],
                    "source_sha256": spec["sha256"], "configure": spec["configure"]}


def linux(root, spec, jobs):
    """The Linux runtime: the pinned native libraries built statically, the static C++
    runtime, and CPython from its pinned source."""
    root.mkdir()
    prefix, native = native_libraries(root, spec, jobs)
    native["static_runtime"] = static_cxx_runtime(prefix)
    python, runtime = python_from_source(root, spec["python"], prefix, jobs)
    env = {"CPPFLAGS": "-I" + str(prefix / "include"), "LDFLAGS": "-L" + str(prefix / "lib"),
           "PKG_CONFIG_PATH": str(prefix / "lib/pkgconfig"),
           "LIBRARY_PATH": str(prefix / "lib"), "C_INCLUDE_PATH": str(prefix / "include"),
           "SEMGREP_LIBEV_ARCHIVE_PATH": str(prefix / "lib/libev.a")}
    (root / "runtime.json").write_text(json.dumps({"python": str(python), "environment": env,
                                                  "native": native, "python_runtime": runtime}, indent=2) + "\n")


def linux_images(directory):
    """Every ELF image under a distribution, with what it needs at load time."""
    images = []
    for path in sorted(directory.rglob("*")):
        if path.is_symlink() or not path.is_file() or not is_elf_image(path):
            continue
        images.append(dict(read_elf(path), path=path.relative_to(directory).as_posix(), sha256=digest(path)))
    return images


def validate_linux_image(image, architecture, maximum):
    if image["architecture"] != architecture:
        raise RuntimeError("Packaged ELF image has another architecture: " + image["path"])
    for version in image["glibc_versions"]:
        if tuple(int(part) for part in version.split(".")) > maximum:
            raise RuntimeError("ELF image needs glibc %s, above the release baseline: %s" % (version, image["path"]))
    for value in image["rpaths"]:
        if value != "$ORIGIN" and not value.startswith("$ORIGIN/"):
            raise RuntimeError("ELF image has a build-host runpath: " + image["path"])


def validate_linux(cli, extracted, glibc_max):
    """The platform report for a Linux onefile build: the launcher depends only on
    glibc, every packaged image stays within the glibc baseline and finds its non-system
    libraries inside the distribution, and the extracted payload equals the standalone one."""
    architecture = LINUX_ARCHITECTURES[platform.machine()]
    maximum = tuple(int(part) for part in glibc_max.split("."))
    outer = dict(read_elf(cli / "opengrep"), path="opengrep", sha256=digest(cli / "opengrep"))
    validate_linux_image(outer, architecture, maximum)
    if outer["rpaths"] or set(outer["dependencies"]) - LINUX_SYSTEM_LIBRARIES:
        raise RuntimeError("Onefile launcher depends on libraries outside glibc")
    standalone = linux_images(cli / "entrypoint.dist")
    extracted_images = linux_images(extracted)
    if standalone != extracted_images:
        raise RuntimeError("Extracted payload differs from the standalone distribution")
    paths = {image["path"] for image in standalone}
    if not {"opengrep.bin", "semgrep/bin/opengrep-core"} <= paths:
        raise RuntimeError("Required engine images are missing from the distribution")
    for image in standalone:
        validate_linux_image(image, architecture, maximum)
        base = Path(image["path"]).parent
        search = [(base / value.removeprefix("$ORIGIN").lstrip("/")).as_posix() for value in image["rpaths"]]
        for library in image["dependencies"]:
            if library in LINUX_SYSTEM_LIBRARIES:
                continue
            if not any(os.path.normpath(os.path.join(directory, library)) in paths for directory in search):
                raise RuntimeError("ELF image %s needs %s, which the distribution does not carry" % (image["path"], library))
    report = {"schema_version": 1, "platform": "linux", "architecture": architecture, "glibc_max": glibc_max,
              "outer": outer, "standalone": standalone, "extracted": extracted_images}
    (cli / "platform-checks.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("macos", "linux", "tree-sitter", "validate-macos", "validate-linux"))
    parser.add_argument("root", type=Path)
    parser.add_argument("lock", type=Path)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--extracted", type=Path, help="validate-linux: the onefile payload as extracted at run time")
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
    if args.mode == "linux":
        linux(root, lock["linux"], args.jobs)
        return
    if args.mode == "validate-linux":
        validate_linux(root, args.extracted.resolve(), lock["linux"]["glibc_max"])
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
