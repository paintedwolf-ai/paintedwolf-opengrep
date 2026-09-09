#!/usr/bin/env python3
"""Retrieve licence evidence from pinned distributions and source revisions."""
import hashlib
import io
import json
import pathlib
import re
import subprocess
import tarfile
import urllib.request
import zipfile

LICENCE_FILE = re.compile(
    r"(^|/)(LICEN[CS]E|COPYING|COPYRIGHT|NOTICE|AUTHORS)([._-][A-Za-z0-9.]+)?$", re.I)
ATTRIBUTION_ONLY = re.compile(r"(^|/)(AUTHORS|NOTICE|COPYRIGHT)([._-][A-Za-z0-9.]+)?$", re.I)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def download(url, cache=None, timeout=180):
    if cache is not None:
        cached = pathlib.Path(cache) / re.sub(r"[^A-Za-z0-9._-]", "_", url)[-180:]
        if cached.exists():
            return cached.read_bytes()
        raw = urllib.request.urlopen(url, timeout=timeout).read()
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(raw)
        return raw
    return urllib.request.urlopen(url, timeout=timeout).read()


def archive_members(raw, name):
    """Yield (path, bytes) for a tar or zip archive held in memory."""
    if name.endswith(".zip") or name.endswith(".whl"):
        archive = zipfile.ZipFile(io.BytesIO(raw))
        for entry in archive.namelist():
            if not entry.endswith("/"):
                yield entry, archive.read(entry)
        return
    archive = tarfile.open(fileobj=io.BytesIO(raw))
    for member in archive.getmembers():
        if member.isfile():
            yield member.name, archive.extractfile(member).read()


def licences_from_archive(raw, name, strip_root=True, max_depth=1):
    """Licence files at or near the archive root, keyed by their path."""
    found = {}
    for path, data in archive_members(raw, name):
        relative = "/".join(path.split("/")[1:]) if strip_root else path
        if not relative or not LICENCE_FILE.search(relative):
            continue
        if relative.count("/") > max_depth:
            continue
        found[relative] = data
    return found


def licences_from_git(url, revision, workdir):
    """Licence files at a pinned git revision, for sources with no release archive."""
    workdir = pathlib.Path(workdir)
    if not (workdir / ".git").exists():
        workdir.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", "--quiet", str(workdir)], check=True)
        subprocess.run(["git", "remote", "add", "origin", url], cwd=workdir, check=True)
    subprocess.run(["git", "fetch", "--quiet", "--depth", "1", "origin", revision],
                   cwd=workdir, check=True)
    listing = subprocess.check_output(["git", "ls-tree", "-r", "FETCH_HEAD", "--name-only"],
                                      cwd=workdir, text=True)
    found = {}
    for path in listing.splitlines():
        if LICENCE_FILE.search(path) and path.count("/") <= 1:
            found[path] = subprocess.check_output(["git", "show", f"FETCH_HEAD:{path}"], cwd=workdir)
    return found


def github_licences(repository, revision, max_depth=None):
    """Licence files at a pinned revision, read through the GitHub tree API.

    Grammar forks vendor their upstream licence deep under `fyi/`, so the depth
    limit is optional here.
    """
    def api(path):
        return json.loads(subprocess.check_output(["gh", "api", path], text=True))

    tree = api(f"/repos/{repository}/git/trees/{revision}?recursive=1")
    found, truncated = {}, tree.get("truncated", False)
    for node in tree.get("tree", []):
        if node["type"] != "blob" or not LICENCE_FILE.search(node["path"]):
            continue
        if max_depth is not None and node["path"].count("/") > max_depth:
            continue
        blob = api(f"/repos/{repository}/git/blobs/{node['sha']}")
        import base64
        found[node["path"]] = base64.b64decode(blob["content"])
    return found, truncated


def github_repository(url):
    match = re.match(r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    return f"{match.group(1)}/{match.group(2)}" if match else None
