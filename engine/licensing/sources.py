#!/usr/bin/env python3
"""Enumerate executable and build components from the frozen dependency inputs."""
import json
import pathlib
import re
import sys

PACKAGE = pathlib.Path(__file__).resolve().parent.parent
LICENSING = PACKAGE / "licensing"
sys.path.insert(0, str(PACKAGE))
from build_support.dependencies import python_distributions

# opam filters that keep a package out of the linked executable.
NOT_LINKED = re.compile(r"\{[^}]*\b(with-test|with-doc|with-dev-setup)\b[^}]*\}")
BUILD_ONLY = re.compile(r"\{[^}]*\bbuild\b[^}]*\}")

# System-library probes and generators do not contribute linked code.
# Native libraries are inventoried through runtimes.json and determinations.json.
GENERATORS = {
    "menhir": "parser generator; only menhirLib/menhirSdk link into the executable",
    "conf-gmp": "probe for GMP; the library itself is pinned in runtimes.json",
    "conf-gmp-powm-sec": "probe for GMP; the library itself is pinned in runtimes.json",
    "conf-libev": "probe for libev; the library itself is pinned in runtimes.json",
    "conf-pkg-config": "build-time probe; nothing links",
    "conf-zlib": "probe for zlib; supplied by the platform",
}


def read_json(path):
    return json.loads(pathlib.Path(path).read_text())


def opam_export(path):
    """Parse an `opam switch export --full` file into package name -> metadata."""
    text = pathlib.Path(path).read_text()
    installed = re.search(r"^installed: \[\n(.*?)^\]$", text, re.S | re.M)
    installed = set(re.findall(r'"([^"]+)"', installed.group(1))) if installed else set()
    packages = {}
    for name, body in re.findall(r'^package "([^"]+)" \{\n(.*?)^\}$', text, re.S | re.M):
        version = re.search(r'^  version: "([^"]+)"', body, re.M)
        licence = re.search(r"^  license: (.+(?:\n    .*)*?)$", body, re.M)
        homepage = re.search(r'^  homepage: "([^"]+)"', body, re.M)
        dev_repo = re.search(r'^  dev-repo: "([^"]+)"', body, re.M)
        url = re.search(r"^  url \{\n(.*?)^  \}$", body, re.S | re.M)
        source = checksum = checksum512 = None
        if url:
            src = re.search(r'src:\s*\n?\s*"([^"]+)"', url.group(1))
            sha = re.search(r"sha256=([0-9a-f]{64})", url.group(1))
            # Some pinned sources provide SHA-512 without SHA-256.
            sha512 = re.search(r"sha512=([0-9a-f]{128})", url.group(1))
            source = src.group(1) if src else None
            checksum = sha.group(1) if sha else None
            checksum512 = sha512.group(1) if sha512 else None
        # VCS pins identify commits; retained source supplies the archive digest.
        git_source = git_revision = None
        if source and source.startswith("git+"):
            git_source, _, git_revision = source[len("git+"):].partition("#")
            source = None
        depends = re.search(r"^  depends: \[\n(.*?)^  \]$", body, re.S | re.M)
        packages[name] = {
            "name": name,
            "version": version.group(1) if version else None,
            "opam_license": re.sub(r"\s+", " ", licence.group(1)).strip() if licence else None,
            "homepage": homepage.group(1) if homepage else None,
            "dev_repo": dev_repo.group(1) if dev_repo else None,
            "source": source,
            "git_source": git_source,
            "git_revision": git_revision,
            "source_sha256": checksum,
            "source_sha512": checksum512,
            "depends_raw": depends.group(1) if depends else "",
        }
    return packages, installed


def runtime_dependencies(entry):
    for line in entry["depends_raw"].splitlines():
        match = re.match(r'\s*"([^"]+)"(.*)', line)
        if not match:
            continue
        name, filters = match.group(1), match.group(2)
        if NOT_LINKED.search(filters) or BUILD_ONLY.search(filters):
            continue
        yield name


def engine_seeds(engine_opam_dir):
    """Runtime dependencies declared by the engine's own opam packages."""
    seeds = set()
    for path in sorted(pathlib.Path(engine_opam_dir).glob("*.opam")):
        block = re.search(r"^depends: \[\n(.*?)^\]$", path.read_text(), re.S | re.M)
        if not block:
            continue
        for line in block.group(1).splitlines():
            match = re.match(r'\s*"([^"]+)"(.*)', line)
            if not match:
                continue
            name, filters = match.group(1), match.group(2)
            if NOT_LINKED.search(filters) or BUILD_ONLY.search(filters):
                continue
            seeds.add(name)
    return seeds


def ocaml_components(export_path, seeds):
    """Derive linkage from dependency metadata for subsequent artifact verification."""
    packages, installed = opam_export(export_path)
    reached, stack = set(), sorted(seeds)
    while stack:
        name = stack.pop()
        if name in reached:
            continue
        reached.add(name)
        if name in GENERATORS or name not in packages:
            continue
        for dependency in runtime_dependencies(packages[name]):
            if dependency not in reached:
                stack.append(dependency)
    components = []
    for name in sorted(packages):
        entry = dict(packages[name])
        entry.pop("depends_raw")
        if name in GENERATORS:
            entry["linkage"] = "build-only"
            entry["linkage_reason"] = GENERATORS[name]
        elif name in reached:
            entry["linkage"] = "static"
            entry["linkage_reason"] = "runtime dependency closure of the engine's opam packages"
        else:
            entry["linkage"] = "build-only"
            entry["linkage_reason"] = "not reachable from the engine's runtime dependencies"
        entry["installed"] = name in installed
        components.append(entry)
    return components


def enumerate_components(package=PACKAGE, engine_submodules=None):
    """Every component of the maintained executable, grouped by kind."""
    lock = read_json(package / "source-lock.json")
    runtimes = read_json(package / "locks/runtimes.json")
    submodules = engine_submodules or read_json(LICENSING / "engine-submodules.json")
    distributions = python_distributions(package)
    python_packages = [dict(entry, linkage="bundled", linkage_reason="locked CLI runtime dependency")
                       for entry in distributions["runtime"]]
    python_packages.extend(dict(entry, linkage="build-only", linkage_reason="locked Python packaging bootstrap")
                           for entry in distributions["bootstrap"])
    return {
        "engine": {
            "name": "opengrep",
            "version": f'{lock["upstream_version"]}+paintedwolf.{lock["patch_version"]}',
            "upstream": lock["upstream"],
            "revision": lock["revision"],
            "interfaces_revision": lock["interfaces_revision"],
        },
        "engine_submodules": submodules,
        "native_grammars": lock["grammars"],
        "ocaml": ocaml_components(package / "locks/macos-arm64.opam.export",
                                  engine_seeds(LICENSING / "engine-opam")),
        "native_libraries": runtimes["macos"]["native_libraries"],
        "tree_sitter": runtimes["tree_sitter"],
        "python_runtime": runtimes["macos"]["python"],
        "python_packages": python_packages,
    }
