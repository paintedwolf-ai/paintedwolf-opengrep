#!/usr/bin/env python3
"""Fetch reviewed distributions and install them without ambient package indexes."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.parse
import urllib.request


MAX_DISTRIBUTION_BYTES = 512 * 1024 * 1024
PYTHON_PLATFORM = "macos-arm64-cp313"


def requirements(path):
    result = []
    names = set()
    for line in Path(path).read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+) --hash=sha256:([a-f0-9]{64})", line)
        if match is None:
            raise ValueError(f"Unhashed or malformed Python requirement in {path}")
        name, version, digest = match.groups()
        canonical = re.sub(r"[-_.]+", "-", name).lower()
        if canonical in names:
            raise ValueError(f"Duplicate Python requirement: {name}")
        names.add(canonical)
        result.append({"name": name, "version": version, "sha256": digest})
    if not result:
        raise ValueError(f"Empty Python requirements: {path}")
    return result


def read_lock(package):
    lock = json.loads((package / "locks/dependencies.json").read_text())
    if lock.get("schema_version") != 1:
        raise ValueError("Unsupported dependency lock")
    return lock


def python_distributions(package, platform=PYTHON_PLATFORM):
    spec = read_lock(package)["python"].get(platform)
    if spec is None:
        raise ValueError(f"No locked Python distributions for {platform}")
    for group, filename in (("bootstrap", "python-bootstrap.txt"), ("runtime", "python.txt")):
        expected = requirements(package / "locks" / filename)
        actual = [{key: entry[key] for key in ("name", "version", "sha256")} for entry in spec[group]]
        if actual != expected:
            raise ValueError(f"Python distribution lock disagrees with {filename}")
    return spec


def verified_file(path, digest, size):
    if (type(size) is not int or not 0 < size <= MAX_DISTRIBUTION_BYTES
            or re.fullmatch(r"[a-f0-9]{64}", digest) is None):
        raise ValueError("Invalid dependency digest or size")
    if path.is_symlink() or not path.is_file() or path.stat().st_size != size:
        raise RuntimeError(f"Dependency size or file type mismatch: {path}")
    actual = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            actual.update(chunk)
    if actual.hexdigest() != digest:
        raise RuntimeError(f"Dependency SHA-256 mismatch: {path}")


class HTTPSRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        if urllib.parse.urlsplit(newurl).scheme != "https":
            raise ValueError("Dependency redirect must use HTTPS")
        return super().redirect_request(request, response, code, message, headers, newurl)


def fetch(spec, destination, *, offline=False):
    filename = spec["filename"]
    url = urllib.parse.urlsplit(spec["url"])
    if (not filename or Path(filename).name != filename or filename in (".", "..")
            or url.scheme != "https" or not url.hostname or url.username or url.password
            or type(spec["bytes"]) is not int or not 0 < spec["bytes"] <= MAX_DISTRIBUTION_BYTES
            or re.fullmatch(r"[a-f0-9]{64}", spec["sha256"]) is None):
        raise ValueError("Invalid dependency distribution pin")
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / filename
    if target.exists() or target.is_symlink():
        verified_file(target, spec["sha256"], spec["bytes"])
        return target
    if offline:
        raise RuntimeError(f"Verified dependency is unavailable offline: {filename}")
    descriptor, temporary_name = tempfile.mkstemp(prefix=".dependency-", dir=destination)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            opener = urllib.request.build_opener(HTTPSRedirects())
            with opener.open(spec["url"], timeout=120) as response:
                count = 0
                while chunk := response.read(min(1024 * 1024, spec["bytes"] + 1 - count)):
                    count += len(chunk)
                    if count > spec["bytes"]:
                        raise RuntimeError(f"Dependency exceeds locked size: {filename}")
                    output.write(chunk)
        verified_file(temporary, spec["sha256"], spec["bytes"])
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def fetch_python(package, destination, platform=PYTHON_PLATFORM, *, offline=False):
    spec = python_distributions(package, platform)
    directory = destination / platform
    for group in ("bootstrap", "runtime"):
        for entry in spec[group]:
            fetch(entry, directory, offline=offline)
    return directory


def install_requirements(python, requirement_file, directory, env=None):
    environment = dict(os.environ if env is None else env)
    environment.update(PIP_CONFIG_FILE=os.devnull, PYTHONNOUSERSITE="1")
    environment.pop("PYTHONPATH", None)
    subprocess.run([str(python), "-I", "-m", "pip", "--isolated", "install", "--no-index", "--no-deps",
                    "--no-cache-dir", "--no-build-isolation", "--require-hashes",
                    "--find-links", str(directory), "-r", str(requirement_file)],
                   env=environment, check=True)


def install_python(python, package, destination, platform=PYTHON_PLATFORM, env=None):
    directory = fetch_python(package, destination, platform, offline=True)
    for filename in ("python-bootstrap.txt", "python.txt"):
        install_requirements(python, package / "locks" / filename, directory, env)
    subprocess.run([str(python), "-I", "-m", "pip", "--isolated", "check"], env=env, check=True)


def install_contract_dependency(python, package, destination):
    entries = python_distributions(package)["runtime"]
    spec = next(entry for entry in entries if entry["name"] == "ruamel.yaml")
    if not spec["filename"].endswith("-none-any.whl"):
        raise ValueError("Contract dependency must be a portable Python wheel")
    fetch(spec, destination)
    with tempfile.TemporaryDirectory(prefix="opengrep-contract-requirements-") as temporary:
        requirement_file = Path(temporary) / "requirements.txt"
        requirement_file.write_text(f'{spec["name"]}=={spec["version"]} --hash=sha256:{spec["sha256"]}\n')
        install_requirements(python, requirement_file, destination)


def grammar_generator(package, destination, generator, platform):
    spec = read_lock(package)["generators"].get(generator, {}).get(platform)
    if spec is None:
        raise ValueError(f"No locked grammar generator for {generator}/{platform}")
    archive = fetch(spec, destination)
    binary = destination / (spec["filename"].removesuffix(".gz"))
    if binary.exists() or binary.is_symlink():
        verified_file(binary, spec["executable_sha256"], spec["executable_bytes"])
        return binary
    descriptor, temporary_name = tempfile.mkstemp(prefix=".generator-", dir=destination)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output, gzip.open(archive, "rb") as source:
            count = 0
            while chunk := source.read(min(1024 * 1024, spec["executable_bytes"] + 1 - count)):
                count += len(chunk)
                if count > spec["executable_bytes"]:
                    raise RuntimeError("Grammar generator exceeds locked size")
                output.write(chunk)
        verified_file(temporary, spec["executable_sha256"], spec["executable_bytes"])
        temporary.chmod(0o755)
        temporary.replace(binary)
    finally:
        temporary.unlink(missing_ok=True)
    return binary


def initialize_opam(root, source, env):
    repository = root / "opam-repository"
    repository.mkdir()
    (repository / "repo").write_text('opam-version: "2.0"\n')
    subprocess.run(["opam", "init", "--bare", "--no-setup", "--no-opamrc", "--disable-sandboxing",
                    "--kind=local", "locked", str(repository), "-y"], cwd=source, env=env, check=True)
