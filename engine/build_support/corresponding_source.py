#!/usr/bin/env python3
"""Retain verified dependency sources required by their licenses."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import urllib.request

PACKAGE = Path(__file__).resolve().parent.parent
RETAINED_LOCK = PACKAGE / "locks/corresponding-source.json"


def digest(raw, algorithm="sha256"):
    return hashlib.new(algorithm, raw).hexdigest()


def verify(entry, raw):
    """Verify source bytes against the recorded digest algorithm."""
    for algorithm in ("sha256", "sha512"):
        expected = entry.get(algorithm)
        if not expected:
            continue
        actual = digest(raw, algorithm)
        if actual != expected:
            raise RuntimeError(f'{entry["id"]}: retained {algorithm} {actual} != pinned {expected}')
        return algorithm
    return None


def retain_archive(entry, destination):
    raw = urllib.request.urlopen(entry["url"], timeout=180).read()
    verified = verify(entry, raw)
    if verified is None:
        raise RuntimeError(f'{entry["id"]}: retained archive has no digest to verify against')
    name = re.sub(r"[^A-Za-z0-9._-]", "_", entry["url"].rsplit("/", 1)[-1]) or "source"
    target = destination / entry["id"].replace("/", "_") / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return {"id": entry["id"], "license": entry["license"], "url": entry["url"],
            "sha256": digest(raw), "bytes": len(raw), "verified_against_pin": verified,
            "retained": target.relative_to(destination).as_posix()}


def retain_git(entry, destination):
    """Archive the pinned source revision."""
    target = destination / entry["id"].replace("/", "_")
    work = target / "clone"
    work.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "--quiet", str(work)], check=True)
    subprocess.run(["git", "remote", "add", "origin", entry["url"]], cwd=work, check=True)
    subprocess.run(["git", "fetch", "--quiet", "--depth", "1", "origin", entry["revision"]],
                   cwd=work, check=True)
    name = entry["id"].rsplit("/", 1)[-1] + ".tar"
    subprocess.run(["git", "archive", "--format=tar", "-o", str(target / name), "FETCH_HEAD"],
                   cwd=work, check=True)
    shutil.rmtree(work)
    raw = (target / name).read_bytes()
    return {"id": entry["id"], "license": entry["license"], "url": entry["url"],
            "revision": entry["revision"], "sha256": digest(raw), "bytes": len(raw),
            "verified_against_pin": None,
            "retained": (target / name).relative_to(destination).as_posix()}


def retain(destination, lock_path=RETAINED_LOCK):
    lock = json.loads(Path(lock_path).read_text())
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    records, unretained = [], []
    for entry in lock["retained"]:
        if not entry["url"]:
            unretained.append({"id": entry["id"], "retained": None, "reason": entry["note"]})
        elif entry.get("revision"):
            records.append(retain_git(entry, destination))
        else:
            records.append(retain_archive(entry, destination))
    manifest = {"schema_version": 1, "artifact_version": lock["artifact_version"],
                "retained": records, "unretained": unretained}
    (destination / "RETAINED-SOURCE.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--lock", type=Path, default=RETAINED_LOCK)
    args = parser.parse_args()
    manifest = retain(args.destination, args.lock)
    print(json.dumps({"retained": len(manifest["retained"]),
                      "unretained": [r["id"] for r in manifest["unretained"]],
                      "bytes": sum(r["bytes"] for r in manifest["retained"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
