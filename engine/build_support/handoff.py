"""Verify bounded artifact transfers between release jobs."""
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tarfile
import tempfile

MAX_FILES = 20000
MAX_BYTES = 4 << 30
MAX_MANIFEST = 16 << 20
STAGES = ("compiled", "inner-signed", "packaged", "outer-signed")


class BoundedStream:
    def __init__(self, source):
        self.source = source
        self.remaining = MAX_BYTES + MAX_MANIFEST + MAX_FILES * 4096

    def read(self, size=-1):
        size = self.remaining + 1 if size < 0 else min(size, self.remaining + 1)
        data = self.source.read(size)
        self.remaining -= len(data)
        require(self.remaining >= 0, "Expanded handoff exceeds its bound")
        return data


class HandoffTarInfo(tarfile.TarInfo):
    def _proc_pax(self, archive):
        require(self.type == tarfile.XHDTYPE and self.size <= 65536, "Unsupported or oversized handoff PAX metadata")
        result = super()._proc_pax(archive)
        require(set(result.pax_headers) <= {"path", "linkpath"}, "Unsupported handoff PAX fields")
        return result

    def _proc_gnulong(self, archive):
        raise ValueError("GNU long headers are not part of the handoff format")

    def _proc_sparse(self, archive):
        raise ValueError("Sparse files are not part of the handoff format")

    def _proc_gnusparse_00(self, next, pax_headers, buf):
        raise ValueError("Sparse files are not part of the handoff format")

    def _proc_gnusparse_01(self, next, pax_headers):
        raise ValueError("Sparse files are not part of the handoff format")

    def _proc_gnusparse_10(self, next, pax_headers, archive):
        raise ValueError("Sparse files are not part of the handoff format")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            result.update(chunk)
    return result.hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate handoff JSON key")
        result[key] = value
    return result


def path_name(name):
    require(isinstance(name, str), "Invalid handoff path")
    path = PurePosixPath(name)
    require(not path.is_absolute() and str(path) == name and ".." not in path.parts
            and len(path.parts) > 1 and path.parts[0] in ("artifact", "cli")
            and "\\" not in name and "\0" not in name, "Invalid handoff path: " + name)
    return path


def inventory(root, *, prefix=""):
    result = {}
    total = 0
    for path in sorted(root.rglob("*")):
        name = (PurePosixPath(prefix) / path.relative_to(root)).as_posix()
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            continue
        path_name(name)
        if stat.S_ISLNK(info.st_mode):
            target = path.resolve(strict=True)
            require(target.is_relative_to(root.resolve()) and (target.is_file() or target.is_dir()),
                    "Handoff symlink escapes its tree")
            result[name] = {"symlink": os.readlink(path)}
        else:
            require(stat.S_ISREG(info.st_mode), "Handoff contains a special file")
            total += info.st_size
            result[name] = {"sha256": digest(path), "bytes": info.st_size, "mode": 0o755 if info.st_mode & 0o111 else 0o644}
        require(len(result) <= MAX_FILES and total <= MAX_BYTES, "Handoff exceeds its bound")
    return result


def validate_manifest(value, source_lock_sha256, stage):
    require(isinstance(value, dict) and set(value) == {"schema_version", "stage", "source_lock_sha256", "build_id", "files"},
            "Malformed native handoff manifest")
    require(type(value["schema_version"]) is int and value["schema_version"] == 1
            and value["stage"] == stage and stage in STAGES
            and value["source_lock_sha256"] == source_lock_sha256, "Handoff stage or source lock mismatch")
    require(isinstance(value["build_id"], str) and re.fullmatch(r"paintedwolf-[a-f0-9]{64}", value["build_id"]),
            "Invalid handoff extraction identity")
    files = value["files"]
    require(isinstance(files, dict) and 0 < len(files) <= MAX_FILES, "Invalid handoff inventory")
    total = 0
    for name, record in files.items():
        path_name(name)
        require(isinstance(record, dict), "Invalid handoff file record")
        if set(record) == {"symlink"}:
            target = record["symlink"]
            require(isinstance(target, str) and target and not PurePosixPath(target).is_absolute()
                    and "\\" not in target and "\0" not in target, "Invalid handoff symlink")
        else:
            require(set(record) == {"sha256", "bytes", "mode"}
                    and isinstance(record["sha256"], str) and re.fullmatch(r"[a-f0-9]{64}", record["sha256"])
                    and type(record["bytes"]) is int and 0 <= record["bytes"] <= MAX_BYTES
                    and type(record["mode"]) is int and record["mode"] in (0o644, 0o755), "Invalid handoff file facts")
            total += record["bytes"]
    require(total <= MAX_BYTES, "Handoff exceeds its size bound")


def write(root, output, source_lock_sha256, stage, build_id):
    require(not output.exists() and not output.is_symlink(), "Handoff output must be new")
    value = {"schema_version": 1, "stage": stage, "source_lock_sha256": source_lock_sha256,
             "build_id": build_id, "files": inventory(root)}
    validate_manifest(value, source_lock_sha256, stage)
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    require(len(raw) <= MAX_MANIFEST, "Handoff manifest exceeds its bound")
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".native-handoff-", dir=output.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as file, gzip.GzipFile(fileobj=file, mode="wb", mtime=0, filename="") as compressed:
            with tarfile.open(fileobj=compressed, mode="w|", format=tarfile.PAX_FORMAT) as archive:
                header = tarfile.TarInfo("handoff.json")
                header.size, header.mode = len(raw), 0o644
                archive.addfile(header, io.BytesIO(raw))
                for name, record in value["files"].items():
                    member = tarfile.TarInfo(name)
                    if "symlink" in record:
                        member.type, member.linkname = tarfile.SYMTYPE, record["symlink"]
                        archive.addfile(member)
                    else:
                        member.size, member.mode = record["bytes"], record["mode"]
                        with (root / name).open("rb") as source:
                            archive.addfile(member, source)
        require(inventory(root) == value["files"], "Handoff changed during packaging")
        require(temporary.stat().st_size <= MAX_BYTES, "Compressed handoff exceeds its bound")
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)


def read(archive_path, root, source_lock_sha256, stage):
    require(stat.S_ISREG(archive_path.lstat().st_mode) and archive_path.stat().st_size <= MAX_BYTES,
            "Handoff must be a bounded regular archive")
    require(not root.exists() and not root.is_symlink(), "Handoff destination must be new")
    root.mkdir()
    with gzip.open(archive_path, "rb") as compressed:
        stream = BoundedStream(compressed)
        value = read_stream(stream, root, source_lock_sha256, stage)
        while tail := stream.read(1 << 20):
            require(not any(tail), "Unexpected data after native handoff")
    require(inventory(root) == value["files"], "Handoff inventory mismatch")
    return value


def read_stream(stream, root, source_lock_sha256, stage):
    with tarfile.open(fileobj=stream, mode="r|", tarinfo=HandoffTarInfo) as archive:
        header = archive.next()
        require(header is not None and header.name == "handoff.json" and header.isfile()
                and 0 < header.size <= MAX_MANIFEST, "Handoff manifest must be first")
        value = json.loads(archive.extractfile(header).read(), object_pairs_hook=unique_object)
        validate_manifest(value, source_lock_sha256, stage)
        seen, links = set(), {}
        for member in archive:
            if member is header:
                continue
            name = member.name
            path_name(name)
            require(name in value["files"] and name not in seen, "Unexpected or duplicate handoff file")
            seen.add(name)
            record = value["files"][name]
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if "symlink" in record:
                require(member.issym() and member.size == 0 and member.linkname == record["symlink"],
                        "Handoff symlink mismatch")
                links[name] = member.linkname
            else:
                require(member.isfile() and member.size == record["bytes"] and member.mode == record["mode"],
                        "Handoff file type, size, or mode mismatch")
                hashed = hashlib.sha256()
                with archive.extractfile(member) as source, target.open("xb") as destination:
                    for chunk in iter(lambda: source.read(1 << 20), b""):
                        hashed.update(chunk)
                        destination.write(chunk)
                require(hashed.hexdigest() == record["sha256"], "Handoff file digest mismatch")
                target.chmod(record["mode"])
        require(seen == set(value["files"]), "Handoff inventory is incomplete")
        while tail := archive.fileobj.read(1 << 20):
            require(not any(tail), "Unexpected data after native handoff")
        for name, target in links.items():
            (root / name).symlink_to(target)
    return value
