"""Explicit macOS signing policy and native, per-image signature verification."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

MACHO_MAGIC = {bytes.fromhex(value) for value in (
    "feedface", "cefaedfe", "feedfacf", "cffaedfe", "cafebabe", "bebafeca", "cafebabf", "bfbafeca")}
MAX_IMAGES = 10000
MAX_IMAGE_BYTES = 8 << 30
MAX_INSPECTOR_OUTPUT = 1 << 20
ADHOC_FLAG = 0x2
RUNTIME_FLAG = 0x10000


def execution_support():
    name = "_opengrep_signing_test_execution"
    if name not in sys.modules:
        path = Path(__file__).resolve().parents[1] / "build_support/test_execution.py"
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


class SigningError(RuntimeError):
    """A failed native check or a mismatch with the requested signing profile."""


@dataclass(frozen=True)
class SigningProfile:
    schema_version: int
    mode: str
    team_id: str | None
    certificate_sha256: str | None

    @classmethod
    def parse(cls, value, platform=None):
        platform = sys.platform if platform is None else platform
        if value is None:
            value = {"schema_version": 1, "mode": "adhoc", "team_id": None, "certificate_sha256": None}
        if not isinstance(value, dict) or set(value) != {"schema_version", "mode", "team_id", "certificate_sha256"}:
            raise SigningError("Signing profile must declare exactly the version, mode, Team ID, and certificate digest")
        if type(value["schema_version"]) is not int or value["schema_version"] != 1:
            raise SigningError("Unsupported signing policy version")
        if value["mode"] == "adhoc":
            if value["team_id"] is not None or value["certificate_sha256"] is not None:
                raise SigningError("Ad-hoc profile cannot specify a Developer ID identity")
        elif value["mode"] == "developer-id":
            if platform != "darwin":
                raise SigningError("Developer ID signing requires macOS")
            if not isinstance(value["team_id"], str) or not re.fullmatch(r"[A-Z0-9]{10}", value["team_id"]):
                raise SigningError("Developer ID profile requires the exact Team ID")
            if not isinstance(value["certificate_sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", value["certificate_sha256"]):
                raise SigningError("Developer ID profile requires the lowercase leaf DER SHA-256")
        else:
            raise SigningError("Unknown signing profile mode")
        return cls(**value)

    def record(self):
        return asdict(self)

    def digest(self):
        return hashlib.sha256(json.dumps(self.record(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def image_digest(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= MAX_IMAGE_BYTES:
        raise SigningError("Signature inspection requires a bounded regular image: " + str(path))
    digest = hashlib.sha256()
    with path.open("rb") as source:
        opened = os.fstat(source.fileno())
        if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
            raise SigningError("Image changed before hashing")
        count = 0
        for chunk in iter(lambda: source.read(1 << 20), b""):
            count += len(chunk)
            if count > info.st_size:
                raise SigningError("Image grew while hashing")
            digest.update(chunk)
        if count != info.st_size:
            raise SigningError("Image size changed while hashing")
    return digest.hexdigest(), info.st_size


def compile_inspector(output, capacity=None):
    if sys.platform != "darwin":
        raise SigningError("Native signature inspection requires macOS")
    capacity = capacity or execution_support().TestCapacity.detect()
    output = Path(output).absolute()
    source = Path(__file__).with_name("native_signatures.m")
    output.parent.mkdir(parents=True, exist_ok=True)
    result = execution_support().run_test_process(["xcrun", "clang", "-fobjc-arc", "-O2", "-Wall", "-Wextra", "-Werror",
                               "-Wno-deprecated-declarations", "-mmacosx-version-min=13.0", str(source),
                               "-framework", "Foundation", "-framework", "Security", "-o", str(output)],
                              timeout=capacity.deadline(120))
    if result.timed_out or result.returncode != 0:
        raise SigningError("Native inspector compilation failed: " + result.stderr[-8192:])
    return output


def validate_inspection(value, profile, expected_digest, expected_bytes):
    SigningProfile.parse(profile.record(), platform="darwin")
    if not isinstance(value, dict) or set(value) != {"schema_version", "ok", "sha256", "bytes", "slices"}:
        raise SigningError("Malformed native signature inspection")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1 or value["ok"] is not True:
        raise SigningError("Native signature validation did not succeed")
    if value["sha256"] != expected_digest or type(value["bytes"]) is not int or value["bytes"] != expected_bytes:
        raise SigningError("Native signature facts describe different image bytes")
    if not isinstance(value["slices"], list) or not 0 < len(value["slices"]) <= 32:
        raise SigningError("Native signature inspection has no bounded architecture inventory")
    seen = set()
    keys = {"architecture", "cpu_type", "cpu_subtype", "identifier", "team_id", "certificate_sha256",
            "secure_timestamp", "flags", "entitlements"}
    for item in value["slices"]:
        if not isinstance(item, dict) or set(item) != keys:
            raise SigningError("Malformed architecture signature facts")
        if any(type(item[key]) is not int or not 0 <= item[key] <= 0xffffffff for key in ("cpu_type", "cpu_subtype", "flags")):
            raise SigningError("Malformed signature numeric facts")
        architecture = (item["cpu_type"], item["cpu_subtype"])
        if architecture in seen:
            raise SigningError("Duplicate architecture signature facts")
        seen.add(architecture)
        if not isinstance(item["architecture"], str) or not re.fullmatch(r"[A-Za-z0-9_]{1,64}", item["architecture"]):
            raise SigningError("Missing architecture identity")
        if not isinstance(item["identifier"], str) or not 0 < len(item["identifier"]) <= 4096:
            raise SigningError("Missing code signing identifier")
        if item["entitlements"] != {}:
            raise SigningError("Engine signing profile permits no entitlements")
        if profile.mode == "developer-id":
            if item["flags"] & ADHOC_FLAG or not item["flags"] & RUNTIME_FLAG:
                raise SigningError("Developer ID image lacks hardened runtime or retains ad-hoc signing")
            if item["team_id"] != profile.team_id or item["certificate_sha256"] != profile.certificate_sha256:
                raise SigningError("Image signer differs from requested Developer ID identity")
            timestamp = item["secure_timestamp"]
            if not isinstance(timestamp, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", timestamp):
                raise SigningError("Image lacks a secure timestamp")
            try:
                datetime.fromisoformat(timestamp.removesuffix("Z") + "+00:00")
            except ValueError as error:
                raise SigningError("Invalid secure timestamp") from error
        elif not item["flags"] & ADHOC_FLAG or any(item[key] is not None for key in ("team_id", "certificate_sha256", "secure_timestamp")):
            raise SigningError("Image does not match the requested ad-hoc profile")
    return value


def inspect_image(helper, image, profile, capacity=None):
    if sys.platform != "darwin":
        raise SigningError("Native signature inspection requires macOS")
    capacity = capacity or execution_support().TestCapacity.detect()
    image = Path(image).absolute()
    SigningProfile.parse(profile.record(), platform="darwin")
    before, size = image_digest(image)
    result = execution_support().run_test_process([str(helper), str(image), profile.mode, profile.team_id or "", profile.certificate_sha256 or ""],
                              timeout=capacity.deadline(120))
    if result.timed_out:
        raise SigningError("Native signature inspection timed out")
    if len(result.stdout.encode()) > MAX_INSPECTOR_OUTPUT:
        raise SigningError("Native signature inspection exceeded its output bound")
    try:
        value = json.loads(result.stdout)
    except (ValueError, TypeError) as error:
        raise SigningError("Native signature inspection returned malformed JSON") from error
    if result.returncode != 0:
        failure = value.get("error", {}) if isinstance(value, dict) else {}
        raise SigningError("Native signature rejection: " + json.dumps(failure, sort_keys=True)[:2048])
    after, after_size = image_digest(image)
    if before != after or size != after_size:
        raise SigningError("Image changed during native signature inspection")
    return validate_inspection(value, profile, before, size)


def profile_from_certificate(helper, certificate, capacity=None):
    if sys.platform != "darwin":
        raise SigningError("Native certificate profile selection requires macOS")
    certificate = Path(certificate).absolute()
    before, size = image_digest(certificate)
    if size > 1 << 20:
        raise SigningError("Certificate exceeds its size bound")
    capacity = capacity or execution_support().TestCapacity.detect()
    result = execution_support().run_test_process([str(helper), "--certificate", str(certificate)], timeout=capacity.deadline(60))
    if result.timed_out or result.returncode != 0 or len(result.stdout.encode()) > MAX_INSPECTOR_OUTPUT:
        raise SigningError("Native certificate profile selection failed: " + result.stdout[:2048])
    try:
        profile = SigningProfile.parse(json.loads(result.stdout), platform="darwin")
    except (ValueError, TypeError) as error:
        raise SigningError("Native certificate profile is malformed") from error
    if profile.mode != "developer-id" or profile.certificate_sha256 != before or image_digest(certificate) != (before, size):
        raise SigningError("Certificate profile describes different bytes")
    return profile


def image_inventory(root):
    """Inspect real files once; symlinks must remain inside the owned tree."""
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise SigningError("Mach-O inventory root is not a directory")
    images = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs + files):
            entry = Path(directory) / name
            if entry.is_symlink():
                try:
                    target = entry.resolve(strict=True)
                    target.relative_to(root)
                except (OSError, RuntimeError, ValueError) as error:
                    raise SigningError("Distribution symlink escapes, loops, or is dangling: " + str(entry)) from error
                if not target.is_dir() and not target.is_file():
                    raise SigningError("Distribution symlink targets a special file")
                continue
            if entry.is_dir():
                continue
            if not stat.S_ISREG(entry.lstat().st_mode):
                raise SigningError("Distribution contains a special file")
            with entry.open("rb") as source:
                magic = source.read(4)
            if magic in MACHO_MAGIC:
                if len(images) >= MAX_IMAGES:
                    raise SigningError("Mach-O inventory exceeds its bound")
                images[entry.relative_to(root).as_posix()] = entry
    if not images:
        raise SigningError("No Mach-O images were found")
    return dict(sorted(images.items()))


def inspect_inventory(helper, root, profile, *, required=(), capacity=None):
    inventory = image_inventory(root)
    if not set(required).issubset(inventory):
        raise SigningError("Required packaged Mach-O image is missing")
    return [{"path": name, **inspect_image(helper, image, profile, capacity)} for name, image in inventory.items()]


def compare_extracted_inventory(standalone, extracted):
    """Require identical relative image names and bytes after private extraction."""
    def identities(records):
        result = {}
        for record in records:
            name = record["path"]
            if name in result:
                raise SigningError("Duplicate inspected image path")
            result[name] = (record["sha256"], record["bytes"])
        if not result:
            raise SigningError("Empty inspected image inventory")
        return result
    if identities(standalone) != identities(extracted):
        raise SigningError("Extracted images differ from the signed standalone distribution")


def verify_inventory_unchanged(root, records):
    inventory = image_inventory(root)
    if set(inventory) != {record["path"] for record in records} or len(inventory) != len(records):
        raise SigningError("Packaged image inventory changed after qualification")
    for record in records:
        if image_digest(inventory[record["path"]]) != (record["sha256"], record["bytes"]):
            raise SigningError("Packaged image changed after qualification")


def validate_signing_record(record, profile, binary_sha256, binary_bytes):
    """Validate recorded policy and image equality; native reuse checks remain separate."""
    if not isinstance(record, dict) or set(record) != {"profile", "profile_sha256", "outer", "standalone", "extracted"}:
        raise SigningError("Malformed build signing record")
    recorded_profile = SigningProfile.parse(record["profile"], platform="darwin")
    if (record["profile"] != profile.record() or recorded_profile.digest() != profile.digest()
            or record["profile_sha256"] != profile.digest()):
        raise SigningError("Build signing record differs from requested profile")
    validate_inspection(record["outer"], profile, binary_sha256, binary_bytes)
    for key in ("standalone", "extracted"):
        records = record[key]
        if not isinstance(records, list) or not 0 < len(records) <= MAX_IMAGES:
            raise SigningError("Missing bounded signed payload inventory")
        names = set()
        for image in records:
            if not isinstance(image, dict) or not isinstance(image.get("path"), str):
                raise SigningError("Malformed signed payload image")
            name = image["path"]
            if name in names or name.startswith("/") or "\\" in name or "\x00" in name or any(part in ("", ".", "..") for part in name.split("/")):
                raise SigningError("Invalid signed payload path")
            names.add(name)
            digest = image.get("sha256")
            size = image.get("bytes")
            if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest) or type(size) is not int or not 0 < size <= MAX_IMAGE_BYTES:
                raise SigningError("Invalid signed payload digest or size")
            validate_inspection({k: v for k, v in image.items() if k != "path"}, profile, digest, size)
        if "semgrep/bin/opengrep-core" not in names:
            raise SigningError("Signed payload lacks the native scanner core")
    compare_extracted_inventory(record["standalone"], record["extracted"])
    if {image["path"]: image for image in record["standalone"]} != {image["path"]: image for image in record["extracted"]}:
        raise SigningError("Extracted signature facts differ from the standalone distribution")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("profile", help="Select an expected signer from a public leaf certificate")
    command.add_argument("--certificate", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="opengrep-signing-profile-") as directory:
        helper = compile_inspector(Path(directory) / "inspect-signatures")
        profile = profile_from_certificate(helper, args.certificate)
    args.output.write_text(json.dumps(profile.record(), sort_keys=True, indent=2) + "\n")


if __name__ == "__main__":
    main()
