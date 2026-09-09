#!/usr/bin/env python3
"""Archive the actual modified engine, grammars, and frozen build inputs."""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import stat
import subprocess
import tarfile


def relative_path(value):
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise RuntimeError("Invalid source archive path: " + value)
    return path


# Exclude separately licensed fixture submodules from the source archive.
TEST_TREES = {"test", "tests"}


def is_test_corpus(name):
    return PurePosixPath(name).parts[0] in TEST_TREES


def tracked_sources(root):
    entries = subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=root)
    for entry in entries.decode().split("\0"):
        if not entry:
            continue
        metadata, name = entry.split("\t", 1)
        mode, revision, stage = metadata.split()
        if stage != "0":
            raise RuntimeError("Unmerged source archive input: " + name)
        path = root / relative_path(name)
        if mode == "160000":
            if is_test_corpus(name):
                continue
            actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()
            if actual != revision:
                raise RuntimeError("Source submodule differs from its revision: " + name)
            yield from tracked_sources(path)
        elif path.exists() or path.is_symlink():
            yield path


def patch_sources(root, patch):
    changes = subprocess.check_output(
        ["git", "apply", "--numstat", "-z", str(patch)], cwd=root)
    for change in changes.decode().split("\0"):
        if not change:
            continue
        path = root / relative_path(change.split("\t", 2)[2])
        if path.exists() or path.is_symlink():
            yield path


def third_party_entries(retained):
    """Retained upstream archives for the works whose licences require source."""
    entries = {}
    for path in sorted(Path(retained).rglob("*")) if retained else []:
        if path.is_file():
            entries["third-party/" + path.relative_to(retained).as_posix()] = path
    return entries


def source_entries(root, package, lock, retained=None):
    engine = root / "engine"
    entries = {"engine/" + path.relative_to(engine).as_posix(): path
               for path in tracked_sources(engine)}
    for path in (package / "source").rglob("*"):
        if path.is_file():
            relative = path.relative_to(package / "source")
            entries["engine/" + relative.as_posix()] = engine / relative
    series = json.loads((package / "patches/series.json").read_text())
    for item in series["patches"]:
        prefix = Path("cli/src/semgrep/semgrep_interfaces") if item["target"] == "interfaces" else Path()
        for path in patch_sources(engine / prefix, package / relative_path(item["patch"])):
            entries["engine/" + path.relative_to(engine).as_posix()] = path
    for grammar in lock["grammars"]:
        name = grammar["language"]
        tree = root / ("grammar-" + name)
        for path in tracked_sources(tree):
            entries["grammars/" + name + "/" + path.relative_to(tree).as_posix()] = path
        if grammar["patch"] is not None:
            patch = package / relative_path(grammar["patch"])
            for path in patch_sources(tree, patch):
                entries["grammars/" + name + "/" + path.relative_to(tree).as_posix()] = path
        for name_in_source in grammar["generated_files"]:
            relative = relative_path(name_in_source)
            installed = Path("include") / relative if relative.suffix == ".h" else Path(relative)
            name_in_archive = "engine/languages/native_scripts/" + name + "/" + installed.as_posix()
            entries[name_in_archive] = engine / "languages/native_scripts" / name / installed
    for name in ["source-lock.json", *lock["files"]]:
        entries["inputs/" + name] = package / relative_path(name)
    entries.update(third_party_entries(retained))
    return entries


def archive_sources(destination, entries, identity, allowed_roots):
    manifest = {"identity": identity, "files": {}}
    allowed_roots = [root.resolve() for root in allowed_roots]
    with destination.open("xb") as output:
        with gzip.GzipFile(fileobj=output, filename="", mode="wb", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|") as archive:
                for name, path in sorted(entries.items()):
                    relative_path(name)
                    if not any(path.parent.resolve().is_relative_to(root) for root in allowed_roots):
                        raise RuntimeError("Source archive input escapes its source tree: " + name)
                    mode = path.lstat().st_mode
                    info = tarfile.TarInfo(name)
                    info.mtime = info.uid = info.gid = 0
                    if stat.S_ISLNK(mode):
                        target = os.readlink(path)
                        if Path(target).is_absolute():
                            raise RuntimeError("Absolute symlink in source archive: " + name)
                        archive_target = posixpath.normpath(str(PurePosixPath(name).parent / target))
                        relative_path(archive_target)
                        info.type, info.linkname, info.mode = tarfile.SYMTYPE, target, 0o777
                        manifest["files"][name] = {"symlink": target}
                        archive.addfile(info)
                    elif stat.S_ISREG(mode):
                        raw = path.read_bytes()
                        info.size = len(raw)
                        info.mode = 0o755 if mode & 0o111 else 0o644
                        manifest["files"][name] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
                        archive.addfile(info, io.BytesIO(raw))
                    else:
                        raise RuntimeError("Non-file source archive input: " + name)
                raw = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
                info = tarfile.TarInfo("SOURCE-MANIFEST.json")
                info.size, info.mode = len(raw), 0o644
                archive.addfile(info, io.BytesIO(raw))
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("package", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--retained", type=Path, default=None,
                        help="directory of retained third-party sources to archive")
    args = parser.parse_args()
    lock_bytes = (args.package / "source-lock.json").read_bytes()
    lock = json.loads(lock_bytes)
    identity = {"base_revision": lock["revision"], "interfaces_revision": lock["interfaces_revision"],
                "source_lock_sha256": hashlib.sha256(lock_bytes).hexdigest()}
    entries = source_entries(args.root, args.package, lock, args.retained)
    roots = [args.root, args.package] + ([args.retained] if args.retained else [])
    archive_sources(args.destination, entries, identity, roots)
    print(json.dumps({"source_archive": str(args.destination), "files": len(entries), **identity}))


if __name__ == "__main__":
    main()
