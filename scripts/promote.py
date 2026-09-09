#!/usr/bin/env python3
"""Verify attested release files and create a complete draft without overwriting a version."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

import release_provenance as PROVENANCE

SPEC = importlib.util.spec_from_file_location("release_pack", Path(__file__).with_name("release.py"))
RELEASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RELEASE)


def release_files(directory, identity):
    metadata = RELEASE.ARTIFACT.read_json(directory / "release.json")
    lock = RELEASE.ARTIFACT.read_json(PROVENANCE.ROOT / "engine/source-lock.json")
    record = metadata["opengrep"]
    for key, expected in (("version", identity["version"]), ("source_lock_sha256", identity["source_lock_sha256"]),
                          ("upstream_version", lock["upstream_version"]), ("revision", lock["patch_version"]),
                          ("base_revision", lock["revision"]), ("origin", "downstream"), ("license", "LGPL-2.1")):
        PROVENANCE.require(record.get(key) == expected, "Release descriptor identity differs: " + key)
    name = "opengrep-" + identity["version"] + "-darwin-arm64.tar.gz"
    archive = directory / name
    expected = {"goos": "darwin", "goarch": "arm64", "sha256": PROVENANCE.digest(archive),
                "bytes": archive.stat().st_size, "url": "https://github.com/" + PROVENANCE.REPOSITORY
                + "/releases/download/" + identity["ref"].removeprefix("refs/tags/") + "/" + name}
    PROVENANCE.require(record.get("artifacts") == [expected], "Release archive differs from descriptor")
    evidence = directory / "build-evidence.json"
    PROVENANCE.check_evidence(RELEASE.ARTIFACT.read_json(evidence), identity)
    files = [archive, directory / "release.json", evidence, directory / "provenance.sigstore.json"]
    PROVENANCE.require({path.name for path in directory.iterdir()} == {path.name for path in files},
                       "Release directory must contain exactly the archive, descriptor, build evidence, and attestation")
    for path in files:
        RELEASE.ARTIFACT.regular(path)
    return files


def validate_uploaded_assets(release, files, identity):
    PROVENANCE.require(release.get("draft") is True and release.get("tag_name") == identity["ref"].removeprefix("refs/tags/"),
                       "Uploaded release is not the expected draft")
    assets = release.get("assets", [])
    expected = {path.name: (path.stat().st_size, "sha256:" + PROVENANCE.digest(path)) for path in files}
    PROVENANCE.require(len(assets) == len(expected) and {asset["name"] for asset in assets} == set(expected),
                       "Draft release does not contain the complete exact asset set")
    for asset in assets:
        PROVENANCE.require(asset.get("state") == "uploaded"
                           and (asset.get("size"), asset.get("digest")) == expected[asset["name"]],
                           "Uploaded asset differs: " + asset["name"])


def draft(directory, identity):
    files = release_files(directory, identity)
    for subject in files[:-1]:
        PROVENANCE.verify_attestation(subject, files[-1], identity)
    PROVENANCE.require_unpublished(identity)
    tag = identity["ref"].removeprefix("refs/tags/")
    with tempfile.TemporaryDirectory(prefix="opengrep-draft-") as temporary:
        notes = Path(temporary) / "notes.md"
        notes.write_text("Qualified Developer ID macOS arm64 engine.\n\nSource commit: " + identity["commit"]
                         + "\nBuild run: https://github.com/" + PROVENANCE.REPOSITORY + "/actions/runs/"
                         + identity["run_id"] + "/attempts/" + identity["run_attempt"]
                         + "\n\nArchive, release descriptor, and build evidence have GitHub-hosted provenance attestations."
                         + " Confirm that immutable releases are enabled before publishing this complete draft.\n")
        subprocess.run(["gh", "release", "create", tag, "--repo", PROVENANCE.REPOSITORY, "--verify-tag", "--draft",
                        "--target", identity["commit"], "--title", tag, "--notes-file", str(notes),
                        *[str(path) for path in files]], check=True)
    pages = json.loads(PROVENANCE.command(["gh", "api", "--paginate", "--slurp",
                                          "repos/" + PROVENANCE.REPOSITORY + "/releases?per_page=100"]))
    matches = [release for page in pages for release in page if release["tag_name"] == tag]
    PROVENANCE.require(len(matches) == 1, "Cannot locate the unique uploaded draft")
    validate_uploaded_assets(matches[0], files, identity)
    return matches[0]["html_url"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    print(draft(args.directory.resolve(), PROVENANCE.checked_identity()))


if __name__ == "__main__":
    main()
