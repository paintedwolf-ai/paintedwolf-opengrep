#!/usr/bin/env python3
"""Package a qualified native build without modifying its executable or provenance."""
import argparse
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "engine"
SPEC = importlib.util.spec_from_file_location("release_artifact", PACKAGE / "artifact.py")
ARTIFACT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ARTIFACT)
PAYLOADS = (*ARTIFACT.REQUIRED, "LICENSE", "NOTICES-opengrep.md")
MAX_MEMBER_BYTES = 512 << 20
MAX_ARCHIVE_BYTES = 512 << 20
MAX_EXPANDED_BYTES = 2 << 30


# Released platforms: the target an artifact is validated as, and where its notices live.
PLATFORMS = {"darwin-arm64": (("darwin", "arm64"), "licensing"),
             "linux-amd64": (("linux", "amd64"), "licensing/linux-amd64")}
# Linux engines build and qualify for development; published releases are macOS only.
RELEASED = ("darwin-arm64",)


def release_notice_bytes(package, lock, platform="darwin-arm64"):
    version = f'{lock["upstream_version"]}+paintedwolf.{lock["patch_version"]}'
    notices = package / PLATFORMS[platform][1]
    identity = ARTIFACT.read_json(notices / "inventory.json")["artifact"]
    for key, expected in (("version", version), ("revision", lock["revision"]),
                          ("interfaces_revision", lock["interfaces_revision"])):
        ARTIFACT.require(identity.get(key) == expected, "Notices inventory identity differs: " + key)
    if platform != "darwin-arm64":
        ARTIFACT.require(identity.get("platform") == platform, "Notices describe another platform")
    raw = ARTIFACT.regular(notices / "NOTICES-opengrep.md").read_bytes()
    ARTIFACT.require(raw.startswith(("# Third-party notices — opengrep " + version + "\n").encode()),
                     "Notices version differs from engine")
    retained = ARTIFACT.read_json(package / "locks/corresponding-source.json")
    ARTIFACT.require(retained.get("artifact_version") == version,
                     "Retained source version differs from engine")
    return raw


def validate_release_artifact(directory, package, channel, scratch, platform="darwin-arm64"):
    if platform == "linux-amd64":
        return validate_linux_artifact(directory, package, scratch)
    lock = ARTIFACT.snapshot_inputs(package, scratch / "inputs")
    provenance = ARTIFACT.read_json(directory / "provenance.json")
    profile = ARTIFACT.signing_module().SigningProfile.parse(provenance["signing"]["profile"], platform="darwin")
    ARTIFACT.require(channel == "prerelease" or profile.mode == "developer-id",
                     "Stable releases require Developer ID; ad-hoc builds are prereleases")
    if channel == "stable":
        expected = ARTIFACT.signing_module().SigningProfile.parse(
            ARTIFACT.read_json(scratch / "inputs/signing/release-profile.json"), platform="darwin")
        ARTIFACT.require(expected.mode == "developer-id" and profile == expected,
                         "Artifact signer differs from the committed release policy")
    target = ARTIFACT.native_target()
    ARTIFACT.require(target == ("darwin", "arm64"), "Only native macOS arm64 release packaging is qualified")
    helper = ARTIFACT.signing_module().compile_inspector(scratch / "signature-inspector")
    inspect = lambda image: ARTIFACT.signing_module().inspect_image(helper, image, profile)
    ARTIFACT.validate_artifact(directory, scratch / "inputs", lock, target, profile=profile, inspect=inspect)
    ARTIFACT.require(inspect(directory / "opengrep") == provenance["signing"]["outer"],
                     "Executable signature differs from build provenance")
    return lock


def validate_linux_artifact(directory, package, scratch):
    """A Linux engine as qualified: no signature to check, every other rule the same.
    Stable and prerelease channels accept it alike, since no signing identity applies."""
    lock = ARTIFACT.snapshot_inputs(package, scratch / "inputs")
    ARTIFACT.require(ARTIFACT.native_target() == ("linux", "amd64"), "Linux packaging runs on linux/amd64")
    ARTIFACT.validate_artifact(directory, scratch / "inputs", lock, ("linux", "amd64"))
    return lock


def write_archive(destination, directory):
    expanded = 1024
    for name in PAYLOADS:
        size = ARTIFACT.regular(directory / name).stat().st_size
        ARTIFACT.require(0 < size <= MAX_MEMBER_BYTES, "Release member exceeds size limit: " + name)
        expanded += 512 + ((size + 511) // 512) * 512
    expanded = ((expanded + tarfile.RECORDSIZE - 1) // tarfile.RECORDSIZE) * tarfile.RECORDSIZE
    ARTIFACT.require(expanded <= MAX_EXPANDED_BYTES, "Release archive exceeds expanded size limit")
    with destination.open("xb") as stream:
        with gzip.GzipFile(fileobj=stream, filename="", mode="wb", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|", format=tarfile.USTAR_FORMAT) as archive:
                for name in sorted(PAYLOADS):
                    raw = ARTIFACT.regular(directory / name).read_bytes()
                    info = tarfile.TarInfo(name)
                    info.size = len(raw)
                    info.mode = 0o755 if name == "opengrep" else 0o644
                    info.mtime = info.uid = info.gid = 0
                    archive.addfile(info, io.BytesIO(raw))
    ARTIFACT.require(destination.stat().st_size <= MAX_ARCHIVE_BYTES, "Release archive exceeds compressed size limit")


def release_metadata(directory, package, lock, tag, archive, target=("darwin", "arm64")):
    with tarfile.open(directory / "opengrep-source.tar.gz", "r:gz") as source:
        manifest = source.extractfile("SOURCE-MANIFEST.json").read()
    version = f'{lock["upstream_version"]}+paintedwolf.{lock["patch_version"]}'
    return {"opengrep": {
        "version": version, "origin": "downstream", "upstream_version": lock["upstream_version"],
        "base_revision": lock["revision"], "revision": lock["patch_version"],
        "source_lock_sha256": ARTIFACT.digest(package / "source-lock.json"),
        "source_manifest_sha256": hashlib.sha256(manifest).hexdigest(), "license": "LGPL-2.1",
        "artifacts": [{"goos": target[0], "goarch": target[1],
            "url": "https://github.com/paintedwolf-ai/paintedwolf-opengrep/releases/download/" + tag + "/" + archive.name,
            "sha256": ARTIFACT.digest(archive), "bytes": archive.stat().st_size}]}}


def pack(artifact, destination, tag, channel, package=PACKAGE, platform="darwin-arm64"):
    ARTIFACT.require(channel in ("prerelease", "stable"), "Unknown release channel")
    ARTIFACT.require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", tag) is not None, "Invalid release tag")
    ARTIFACT.require(not destination.exists(), "Release output directory must not already exist")
    ARTIFACT.artifact_tree(artifact)
    with tempfile.TemporaryDirectory(prefix="opengrep-release-") as temporary:
        scratch = Path(temporary)
        staged = scratch / "artifact"
        staged.mkdir()
        for name in PAYLOADS:
            if name != "NOTICES-opengrep.md":
                shutil.copy2(ARTIFACT.regular(artifact / name), staged / name)
        lock = validate_release_artifact(staged, package, channel, scratch, platform)
        version = f'{lock["upstream_version"]}+paintedwolf.{lock["patch_version"]}'
        ARTIFACT.require(tag == "v" + version, "Release tag must match the exact engine version")
        (staged / "NOTICES-opengrep.md").write_bytes(release_notice_bytes(package, lock, platform))
        output = scratch / "release"
        output.mkdir()
        archive = output / ("opengrep-" + version + "-" + platform + ".tar.gz")
        write_archive(archive, staged)
        metadata = release_metadata(staged, scratch / "inputs", lock, tag, archive, PLATFORMS[platform][0])
        (output / "release.json").write_text(json.dumps(metadata, sort_keys=True, indent=2) + "\n")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(output, destination)
    return metadata


def merge(sources, destination):
    """One release from per-platform packaging outputs: every archive checked against the
    descriptor that named it, and one descriptor listing all of them."""
    ARTIFACT.require(not destination.exists(), "Release output directory must not already exist")
    ARTIFACT.require(len(sources) == len(RELEASED), "A release carries every released platform")
    shared, artifacts, archives = None, [], []
    for source in sources:
        descriptor = ARTIFACT.read_json(source / "release.json")["opengrep"]
        rows = descriptor.pop("artifacts")
        ARTIFACT.require(len(rows) == 1, "Each platform output names exactly one archive")
        ARTIFACT.require(shared is None or descriptor == shared, "Platform outputs describe different engines")
        shared = descriptor
        row = rows[0]
        archive = source / row["url"].rsplit("/", 1)[1]
        ARTIFACT.require({path.name for path in source.iterdir()} == {"release.json", archive.name},
                         "Platform output must contain exactly its archive and descriptor")
        ARTIFACT.require(ARTIFACT.digest(archive) == row["sha256"] and archive.stat().st_size == row["bytes"],
                         "Platform archive differs from its descriptor: " + archive.name)
        artifacts.append(row)
        archives.append(archive)
    platforms = sorted((row["goos"], row["goarch"]) for row in artifacts)
    ARTIFACT.require(platforms == sorted(PLATFORMS[name][0] for name in RELEASED),
                     "A release carries each released platform once")
    destination.mkdir(parents=True)
    for archive in archives:
        shutil.copy2(archive, destination / archive.name)
    metadata = {"opengrep": dict(shared, artifacts=sorted(artifacts, key=lambda row: (row["goos"], row["goarch"])))}
    (destination / "release.json").write_text(json.dumps(metadata, sort_keys=True, indent=2) + "\n")
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-inputs", action="store_true",
                        help="Validate release metadata without building or packaging an artifact")
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--tag")
    parser.add_argument("--channel", choices=("prerelease", "stable"))
    parser.add_argument("--platform", choices=sorted(PLATFORMS), default="darwin-arm64")
    parser.add_argument("--merge", type=Path, nargs="+", metavar="PLATFORM_OUTPUT",
                        help="Combine per-platform packaging outputs into one release at --output")
    args = parser.parse_args()
    packaging = (args.artifact, args.output, args.tag, args.channel)
    if args.check_inputs and (any(value is not None for value in packaging) or args.merge):
        parser.error("--check-inputs does not accept packaging arguments")
    if args.merge and (args.output is None or any(value is not None for value in (args.artifact, args.tag, args.channel))):
        parser.error("--merge takes only per-platform outputs and --output")
    if not args.check_inputs and not args.merge and any(value is None for value in packaging):
        parser.error("packaging requires --artifact, --output, --tag, and --channel")
    try:
        if args.check_inputs:
            lock = ARTIFACT.read_json(PACKAGE / "source-lock.json")
            for platform in PLATFORMS:
                release_notice_bytes(PACKAGE, lock, platform)
            print("Opengrep release metadata verified")
            return
        if args.merge:
            metadata = merge([path.resolve() for path in args.merge], args.output.resolve())
        else:
            metadata = pack(args.artifact.resolve(), args.output.resolve(), args.tag, args.channel, platform=args.platform)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.CalledProcessError, tarfile.TarError) as error:
        parser.exit(1, "Release packaging: " + str(error) + "\n")
    print(json.dumps(metadata, sort_keys=True))


if __name__ == "__main__":
    main()
