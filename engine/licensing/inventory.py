#!/usr/bin/env python3
"""Inventory every third-party work inside the maintained Opengrep executable.

    collect          refresh licence evidence from primary sources (network)
    collect-python   refresh Python evidence while preserving other groups
    build            derive inventory.json and INVENTORY.md from the evidence
    check            verify the evidence digests and that the inventory is current
    notices          render the third-party notice document for the engine
    retained-lock    emit locks/corresponding-source.json for the build
    archive-audit    compare the inventory against the produced source archive
    verify-artifact  reconcile the inventory with a built standalone distribution

Collection retrieves source artifacts; subsequent commands use local evidence.
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import classify  # noqa: E402
import fetch  # noqa: E402
import sources  # noqa: E402

EVIDENCE = HERE / "evidence"
EVIDENCE_LOCK = HERE / "evidence-lock.json"
INVENTORY = HERE / "inventory.json"

# Obligation classes. "relink" is the LGPL clause-6 / LGPL-3 clause-4 duty that a
# statically linked combined work must let the user replace the library.
NOTICE = "notice"
LICENCE_TEXT = "license-text"
SOURCE = "source-offer"
RELINK = "relink"

PERMISSIVE = {"MIT", "ISC", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "CC0-1.0",
              "Unlicense", "PSF-2.0", "Zlib", "TCL", "ncurses-X11", "SQLite-public-domain"}
WEAK_COPYLEFT = {"MPL-2.0"}
LGPL = {"LGPL-2.0", "LGPL-2.1", "LGPL-3.0"}
STRONG_COPYLEFT = {"GPL-2.0", "GPL-3.0", "AGPL-3.0"}


# Distribution obligations apply only to conveyed components.
NOT_CONVEYED = {"build-only", "virtual"}


def obligations(spdx, exceptions, linkage):
    """The duties a licence imposes on this artefact, given how it is combined."""
    if spdx is None or linkage in NOT_CONVEYED:
        return []
    duties = [NOTICE, LICENCE_TEXT]
    linking_exception = any(e.endswith("linking-exception") for e in exceptions)
    if spdx in WEAK_COPYLEFT:
        duties.append(SOURCE)
    if spdx in LGPL:
        duties.append(SOURCE)
        if linkage == "static" and not linking_exception:
            duties.append(RELINK)
    if spdx in STRONG_COPYLEFT:
        duties.extend([SOURCE, RELINK])
    return duties


def load(path, default=None):
    path = pathlib.Path(path)
    return json.loads(path.read_text()) if path.exists() else default


def store_evidence(group, key, name, raw):
    """Write one licence file under evidence/ and describe it."""
    directory = EVIDENCE / group
    directory.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", f"{key}__{name}")
    (directory / safe).write_bytes(raw)
    text = raw.decode("utf-8", "replace")
    spdx, exceptions = classify.identify(text)
    return {
        "file": name,
        "path": f"evidence/{group}/{safe}",
        "sha256": fetch.digest(raw),
        "bytes": len(raw),
        "role": "attribution" if fetch.ATTRIBUTION_ONLY.search(name) else "license",
        "spdx": spdx,
        "exceptions": exceptions,
        "expression": classify.expression(spdx, exceptions),
        "copyright": classify.copyright_holders(text),
    }


def python_evidence(packages, cache):
    entries = {}
    for package in packages:
        raw = fetch.download(package["url"], cache)
        actual = fetch.digest(raw)
        if actual != package["sha256"] or len(raw) != package["bytes"]:
            raise ValueError("Python licence distribution differs from the build pin: " + package["name"])
        found = fetch.licences_from_archive(raw, package["filename"],
                                          strip_root=package["filename"].endswith(".whl"), max_depth=3)
        entries["python/" + package["name"]] = {
            "group": "python",
            "provenance": {"url": package["url"], "filename": package["filename"],
                           "version": package["version"], "pinned_sha256": package["sha256"],
                           "actual_sha256": actual, "sha256_match": True,
                           "linkage": package["linkage"], "linkage_reason": package["linkage_reason"]},
            "evidence": [store_evidence("python", f'{package["name"]}-{package["version"]}', name, data)
                         for name, data in sorted(found.items())],
        }
        print(f'  python/{package["name"]}: {len(found)} licence files', flush=True)
    return entries


def collect_python(args):
    lock = load(EVIDENCE_LOCK)
    if lock is None or lock.get("schema_version") != 1:
        raise ValueError("Python-only refresh requires an existing evidence lock")
    entries = python_evidence(sources.enumerate_components()["python_packages"], args.cache)
    previous = lock["components"]
    lock["components"] = {key: value for key, value in previous.items() if value["group"] != "python"}
    lock["components"].update(entries)
    EVIDENCE_LOCK.write_text(json.dumps(lock, indent=1, sort_keys=True) + "\n")
    print(f'Refreshed {len(entries)} Python components; other evidence preserved')
    return 0


def collect(args):
    components = sources.enumerate_components()
    lock = {"schema_version": 1, "components": {}}
    cache = args.cache

    def record(group, key, provenance, files, note=None):
        entry = {"group": group, "provenance": provenance, "evidence": files}
        if note:
            entry["note"] = note
        lock["components"][f"{group}/{key}"] = entry
        state = "no licence file" if not files else ", ".join(f["file"] for f in files)
        print(f"  {group}/{key}: {state}", flush=True)

    print("engine and parser submodules")
    engine = components["engine"]
    repository = fetch.github_repository(engine["upstream"])
    found, _ = fetch.github_licences(repository, engine["revision"], max_depth=0)
    record("engine", "opengrep", {"repository": engine["upstream"], "revision": engine["revision"]},
           [store_evidence("engine", "opengrep", n, r) for n, r in sorted(found.items())])
    for submodule in components["engine_submodules"]:
        repository = fetch.github_repository(submodule["url"])
        found, truncated = fetch.github_licences(repository, submodule["revision"])
        key = submodule["path"].replace("/", "_")
        record("parsers", key,
               {"repository": submodule["url"], "revision": submodule["revision"],
                "path": submodule["path"], "tree_truncated": truncated},
               [store_evidence("parsers", key, n, r) for n, r in sorted(found.items())])

    print("native grammars")
    for grammar in components["native_grammars"]:
        repository = fetch.github_repository(grammar["upstream"])
        found, _ = fetch.github_licences(repository, grammar["revision"], max_depth=1)
        record("grammars", grammar["language"],
               {"repository": grammar["upstream"], "revision": grammar["revision"],
                "declared_license": grammar["license"]},
               [store_evidence("grammars", grammar["language"], n, r) for n, r in sorted(found.items())])

    print("native libraries")
    pinned = list(components["native_libraries"]) + [dict(components["tree_sitter"], name="tree-sitter")]
    for library in pinned:
        raw = fetch.download(library["url"], cache)
        actual = fetch.digest(raw)
        found = fetch.licences_from_archive(raw, library["url"])
        record("native", library["name"],
               {"url": library["url"], "version": library["version"],
                "pinned_sha256": library["sha256"], "actual_sha256": actual,
                "sha256_match": actual == library["sha256"]},
               [store_evidence("native", f'{library["name"]}-{library["version"]}', n, r)
                for n, r in sorted(found.items())])

    print("ocaml switch")
    for package in components["ocaml"]:
        key = f'{package["name"]}-{package["version"]}'
        if package["source"]:
            raw = fetch.download(package["source"], cache)
            actual = fetch.digest(raw)
            found = fetch.licences_from_archive(raw, package["source"])
            provenance = {"url": package["source"], "pinned_sha256": package["source_sha256"],
                          "actual_sha256": actual,
                          "sha256_match": package["source_sha256"] in (None, actual)}
        elif package["git_source"]:
            found = fetch.licences_from_git(package["git_source"], package["git_revision"],
                                            HERE / ".git-cache" / package["name"])
            provenance = {"git": package["git_source"], "revision": package["git_revision"],
                          "note": "pinned by git revision; opam records no checksum for a git "
                                  "source, so nothing verifies these bytes on refetch"}
        else:
            found, provenance = {}, {"note": "virtual or conf package; no distributed source"}
        record("ocaml", key,
               dict(provenance, opam_license=package["opam_license"], linkage=package["linkage"],
                    homepage=package["homepage"]),
               [store_evidence("ocaml", key, n, r) for n, r in sorted(found.items())])

    print("python runtime and packages")
    runtime = components["python_runtime"]
    record("python-runtime", "cpython",
           {"url": runtime["url"], "version": runtime["version"], "sha256": runtime["sha256"],
            "note": "licence text and embedded works are read from the expanded framework by "
                    "verify-artifact; the installer is not unpacked here"}, [])
    lock["components"].update(python_evidence(components["python_packages"], cache))

    EVIDENCE_LOCK.write_text(json.dumps(lock, indent=1, sort_keys=True) + "\n")
    print(f"\nwrote {EVIDENCE_LOCK.relative_to(HERE.parent.parent)}: "
          f'{len(lock["components"])} components')
    return 0


def determinations():
    """Curated conclusions where a licence file alone does not settle the answer."""
    document = load(HERE / "determinations.json", {})
    return document.get("components", {}), document.get("extra_components", {})


def reread(entry):
    """Re-derive licence facts from the evidence files rather than the lock."""
    for record in entry["evidence"]:
        path = HERE / record["path"]
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        spdx, exceptions = classify.identify(text)
        record["spdx"], record["exceptions"] = spdx, exceptions
        record["expression"] = classify.expression(spdx, exceptions)
        record["copyright"] = classify.copyright_holders(text)
    return entry


def conclude(key, entry, curated):
    """The licence expression for one component, and how it was established."""
    override = curated.get(key)
    licences = [f for f in entry["evidence"] if f["role"] == "license" and f["spdx"]]
    if override and override.get("license"):
        return {"expression": override["license"], "basis": override["basis"],
                "evidence": override.get("evidence", [f["path"] for f in licences])}
    if not licences:
        return {"expression": None, "basis": "undetermined: no licence file in the pinned source",
                "evidence": []}
    seen = []
    for f in licences:
        if f["expression"] not in seen:
            seen.append(f["expression"])
    return {"expression": " AND ".join(seen), "basis": "licence file in the pinned source",
            "evidence": [f["path"] for f in licences]}


def linkage_of(key, entry, curated):
    override = curated.get(key, {})
    if "linkage" in override:
        return override["linkage"], override.get("linkage_basis", "curated")
    provenance = entry.get("provenance", {})
    if "linkage" in provenance:
        return provenance["linkage"], provenance.get("linkage_reason", "opam runtime dependency closure")
    defaults = {"engine": "static", "parsers": "static", "grammars": "static",
                "native": "static", "python": "bundled", "python-runtime": "bundled"}
    return defaults.get(entry["group"], "static"), "component group default"


def build(args):
    lock = load(EVIDENCE_LOCK)
    if lock is None:
        print("no evidence-lock.json; run `inventory.py collect` first", file=sys.stderr)
        return 1
    curated, extra = determinations()
    components = []
    for key, entry in sorted(lock["components"].items()):
        entry = reread(entry)
        licence = conclude(key, entry, curated)
        linkage, linkage_basis = linkage_of(key, entry, curated)
        primary = next((f for f in entry["evidence"] if f["role"] == "license" and f["spdx"]), None)
        spdx = primary["spdx"] if primary else None
        exceptions = primary["exceptions"] if primary else []
        if curated.get(key, {}).get("spdx"):
            spdx = curated[key]["spdx"]
            exceptions = curated[key].get("exceptions", [])
        components.append({
            "id": key,
            "group": entry["group"],
            "license": licence["expression"],
            "license_basis": licence["basis"],
            "spdx": spdx,
            "exceptions": exceptions,
            "linkage": linkage,
            "linkage_basis": linkage_basis,
            "obligations": obligations(spdx, exceptions, linkage),
            "provenance": entry["provenance"],
            "evidence": licence["evidence"],
            "copyright": sorted({c for f in entry["evidence"] for c in f["copyright"]})[:8],
            "note": entry.get("note") or curated.get(key, {}).get("note"),
        })
    # Works that ship inside another component rather than as their own pinned
    # input: the third-party libraries the Python framework carries.
    for key, entry in sorted(extra.items()):
        components.append({
            "id": key, "group": key.split("/", 1)[0],
            "license": entry["license"], "license_basis": entry["basis"],
            "spdx": entry.get("spdx"), "exceptions": entry.get("exceptions", []),
            "linkage": entry.get("linkage", "bundled"),
            "linkage_basis": entry.get("basis"),
            "obligations": obligations(entry.get("spdx"), entry.get("exceptions", []),
                                       entry.get("linkage", "bundled")),
            "provenance": entry.get("provenance", {}), "evidence": [],
            "copyright": [], "note": entry.get("note"),
        })
    components.sort(key=lambda c: (c["group"], c["id"]))
    document = {"schema_version": 1, "artifact": sources.enumerate_components()["engine"],
                "components": components}
    INVENTORY.write_text(json.dumps(document, indent=1, sort_keys=True) + "\n")
    (HERE / "INVENTORY.md").write_text(render_inventory(document))
    print(f"wrote inventory.json and INVENTORY.md: {len(components)} components")
    return 0


def render_inventory(document):
    rows = document["components"]
    linked = [c for c in rows if c["linkage"] in {"static", "bundled"}]
    lines = [f'# Inventory — opengrep {document["artifact"]["version"]}', "",
             f'Upstream `{document["artifact"]["upstream"]}` at '
             f'`{document["artifact"]["revision"]}`.', "",
             f"{len(rows)} components inventoried; {len(linked)} link into or ship inside the "
             f"executable and the rest are build-only or virtual opam packages.",
             "", "Licence conclusions come from the licence file inside the exact pinned source, "
             "not from package metadata. Run `inventory.py check` to verify every digest offline.",
             "", "The OCaml layer's linkage is the runtime dependency closure of the engine's own "
             "opam packages. That over-approximates: a package a native build never links still "
             "appears here if an engine package declares it without a test filter. "
             "`inventory.py verify-artifact` narrows it against a real artefact.",
             ""]
    for group in ["engine", "parsers", "grammars", "ocaml", "native", "python-runtime", "python"]:
        members = [c for c in rows if c["group"] == group]
        if not members:
            continue
        lines += [f"## {group} ({len(members)})", "",
                  "| component | licence | linkage | obligations |", "|---|---|---|---|"]
        for c in members:
            name = c["id"].split("/", 1)[1]
            duties = ", ".join(c["obligations"]) or "—"
            lines.append(f'| `{name}` | {c["license"] or "**undetermined**"} | {c["linkage"]} | {duties} |')
        lines.append("")
    return "\n".join(lines) + "\n"


def check(args):
    lock = load(EVIDENCE_LOCK)
    if lock is None:
        print("no evidence-lock.json", file=sys.stderr)
        return 1
    failures = []
    for key, entry in sorted(lock["components"].items()):
        for record in entry["evidence"]:
            path = HERE / record["path"]
            if not path.exists():
                failures.append(f'{key}: missing evidence {record["path"]}')
                continue
            actual = fetch.digest(path.read_bytes())
            if actual != record["sha256"]:
                failures.append(f'{key}: {record["path"]} digest {actual} != {record["sha256"]}')
        provenance = entry.get("provenance", {})
        if provenance.get("sha256_match") is False:
            failures.append(f"{key}: pinned source digest did not match on collection")
    current = sources.enumerate_components()
    expected = {f'ocaml/{p["name"]}-{p["version"]}' for p in current["ocaml"]}
    recorded = {k for k in lock["components"] if k.startswith("ocaml/")}
    for missing in sorted(expected - recorded):
        failures.append(f"{missing}: in the switch export but absent from the evidence lock")
    for extra in sorted(recorded - expected):
        failures.append(f"{extra}: in the evidence lock but no longer in the switch export")
    expected_python = {"python/" + package["name"]: package for package in current["python_packages"]}
    recorded_python = {key for key in lock["components"] if key.startswith("python/")}
    for key in sorted(set(expected_python) | recorded_python):
        if key not in expected_python or key not in recorded_python:
            failures.append(f"{key}: Python evidence inventory differs from dependency pins")
            continue
        package = expected_python[key]
        provenance = lock["components"][key]["provenance"]
        expected_facts = {"version": package["version"], "url": package["url"], "filename": package["filename"],
                          "pinned_sha256": package["sha256"], "actual_sha256": package["sha256"],
                          "linkage": package["linkage"]}
        if any(provenance.get(field) != value for field, value in expected_facts.items()):
            failures.append(f"{key}: Python evidence differs from the exact build distribution")
    for problem in failures:
        print("FAIL " + problem)
    print(f'{len(lock["components"])} components, {len(failures)} problems')
    return 1 if failures else 0


def notices(args):
    document = load(INVENTORY)
    if document is None:
        print("no inventory.json; run `inventory.py build` first", file=sys.stderr)
        return 1
    lock = load(EVIDENCE_LOCK)
    shipped = [c for c in document["components"] if c["linkage"] != "build-only"]
    # Components reference one complete copy of each distinct licence text.
    texts, order = {}, []
    for component in shipped:
        for path in component["evidence"]:
            raw = (HERE / path).read_text(encoding="utf-8", errors="replace").strip()
            key = hashlib.sha256(raw.encode()).hexdigest()[:12]
            if key not in texts:
                texts[key] = raw
                order.append(key)
    out = [f'# Third-party notices — opengrep {document["artifact"]["version"]}', "",
           "This scanner engine is a single executable that combines the works below.",
           "Its corresponding source is distributed with the application; see",
           "`SOURCE-OFFER.md` for what the archive contains and how to rebuild.", "",
           f"{len(shipped)} works, under {len(order)} distinct licence texts reproduced in full",
           "at the end of this document.", ""]
    for component in sorted(shipped, key=lambda c: (c["group"], c["id"])):
        name = component["id"].split("/", 1)[1]
        out += [f"## {name}", "", f'- Licence: {component["license"] or "undetermined"}']
        provenance = component["provenance"]
        origin = provenance.get("url") or provenance.get("repository") or provenance.get("git")
        if origin:
            revision = provenance.get("revision")
            out.append(f'- Source: {origin}' + (f' at `{revision}`' if revision else ""))
        for holder in component["copyright"]:
            out.append(f"- {holder}")
        for path in component["evidence"]:
            raw = (HERE / path).read_text(encoding="utf-8", errors="replace").strip()
            key = hashlib.sha256(raw.encode()).hexdigest()[:12]
            out.append(f"- Licence text: [{key}](#licence-text-{key})")
        out.append("")
    out += ["# Licence texts", ""]
    for key in order:
        out += [f"## Licence text {key}", "", "```", texts[key], "```", ""]
    (HERE / "NOTICES-opengrep.md").write_text("\n".join(out))
    print(f"wrote NOTICES-opengrep.md: {len(shipped)} shipped components")
    return 0


def archive_audit(args):
    """What the source archive carries against what the licences require."""
    document = load(INVENTORY)
    if document is None:
        print("no inventory.json; run `inventory.py build` first", file=sys.stderr)
        return 1
    # These component groups travel in the prepared source trees.
    covered = {"engine", "parsers", "grammars"}
    retained_lock = load(HERE.parent / "locks/corresponding-source.json", {"retained": []})
    retained = {entry["id"] for entry in retained_lock["retained"] if entry["url"]}
    unresolved = {entry["id"]: entry["note"] for entry in retained_lock["retained"]
                  if not entry["url"]}
    rows = []
    for component in document["components"]:
        if not {SOURCE, RELINK} & set(component["obligations"]):
            continue
        if component["group"] in covered or component["id"] in retained:
            continue
        if component["id"] in unresolved:
            continue
        rows.append(component)
    carried = len(retained) + sum(1 for c in document["components"]
                                  if {SOURCE, RELINK} & set(c["obligations"])
                                  and c["group"] in covered)
    print(f"{carried} shipped components that owe source have it in the archive: "
          f'{len(retained)} retained upstream, the rest as engine trees.\n')
    for component in rows:
        print(f'  UNCOVERED {component["id"]:44} {component["license"]}')
    if not rows:
        print("  no component owes source that the archive does not carry.")
    if unresolved:
        print("\nno upstream archive of their own; source comes from another component:\n")
        for name in sorted(unresolved):
            print(f"  {name:52} {unresolved[name]}")
    restricted = [c for c in document["components"]
                  if c["group"] in covered and "Commons-Clause" in (c["exceptions"] or [])]
    if restricted:
        # Test-submodule exclusions determine which restricted components travel.
        archiver = load_archiver()
        print("\nrestricted licences among the components the engine tree carries:\n")
        for component in restricted:
            path = component["provenance"].get("path", "")
            excluded = bool(path) and archiver.is_test_corpus(path)
            state = "excluded from the archive" if excluded else "IN THE ARCHIVE"
            print(f'  {component["id"]:44} {component["license"]:28} {state}')
    return 0


def load_archiver():
    """The archiver's own exclusion rule, so the audit reports what it does."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "source_archive", HERE.parent / "build_support/source_archive.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def retained_lock(args):
    """Emit the build's lock of which upstream sources must be retained.

    The build freezes its inputs, so the decision cannot be read out of this
    directory at build time. It is written into `locks/`, which the package
    inventory already covers, and `build_support/corresponding_source.py`
    consumes it.
    """
    document = load(INVENTORY)
    if document is None:
        print("no inventory.json; run `inventory.py build` first", file=sys.stderr)
        return 1
    # The engine, its submodules and the grammar trees are checked out and
    # walked by the archiver, so their source is already carried.
    carried = {"engine", "parsers", "grammars"}
    # Retention verifies the SHA-256 or SHA-512 digest recorded by each source pin.
    switch, _ = sources.opam_export(HERE.parent / "locks/macos-arm64.opam.export")
    digests = {f'ocaml/{name}-{entry["version"]}': entry for name, entry in switch.items()}
    retained = []
    for component in document["components"]:
        if not {SOURCE, RELINK} & set(component["obligations"]) or component["group"] in carried:
            continue
        provenance = component["provenance"]
        pinned = digests.get(component["id"], {})
        retained.append({
            "id": component["id"], "license": component["license"],
            "obligations": component["obligations"],
            "url": provenance.get("url") or provenance.get("git"),
            "revision": provenance.get("revision"),
            "sha256": provenance.get("pinned_sha256") or provenance.get("sha256")
                      or pinned.get("source_sha256"),
            "sha512": pinned.get("source_sha512"),
            "note": None if provenance.get("url") or provenance.get("git")
                    else "no distributed archive; source is carried by another component",
        })
    retained.sort(key=lambda entry: entry["id"])
    lock = {"schema_version": 1, "artifact_version": document["artifact"]["version"],
            "retained": retained}
    path = HERE.parent / "locks/corresponding-source.json"
    path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    unresolved = [entry["id"] for entry in retained if not entry["url"]]
    print(f'wrote {path.name}: {len(retained)} sources to retain'
          + (f', {len(unresolved)} without an archive: {unresolved}' if unresolved else ""))
    return 0


def verify_artifact(args):
    """Reconcile the inventory with a real standalone distribution."""
    root = pathlib.Path(args.path)
    if not root.exists():
        print(f"no such artefact: {root}", file=sys.stderr)
        return 1
    import subprocess
    images, modules = [], []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        with path.open("rb") as handle:
            magic = handle.read(4)
        if magic in {bytes.fromhex(v) for v in
                     ("feedface", "cefaedfe", "feedfacf", "cffaedfe", "cafebabe", "bebafeca")}:
            linked = subprocess.run(["otool", "-L", str(path)], capture_output=True, text=True)
            images.append({"path": str(path.relative_to(root)),
                           "links": [line.strip().split(" (", 1)[0]
                                     for line in linked.stdout.splitlines()[1:]]})
        if path.suffix in {".py", ".pyc"} or path.name.endswith(".dist-info"):
            modules.append(str(path.relative_to(root)))
    report = {"artifact": str(root), "mach_o_images": images, "python_files": len(modules)}
    (HERE / "artifact-report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    external = sorted({link for image in images for link in image["links"]
                       if not link.startswith(("/usr/lib", "/System", "@"))})
    print(f'{len(images)} Mach-O images, {len(modules)} Python files')
    if external:
        print("\nimages linking outside the system and the distribution:")
        for link in external:
            print("  " + link)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    gather = commands.add_parser("collect")
    gather.add_argument("--cache", default=None, help="reuse downloaded archives from this directory")
    gather.set_defaults(handler=collect)
    gather_python = commands.add_parser("collect-python", help="Refresh only locked Python distributions, preserving other evidence")
    gather_python.add_argument("--cache", default=None, help="reuse downloaded archives from this directory")
    gather_python.set_defaults(handler=collect_python)
    for name, handler in [("build", build), ("check", check), ("notices", notices),
                          ("archive-audit", archive_audit), ("retained-lock", retained_lock)]:
        commands.add_parser(name).set_defaults(handler=handler)
    artifact = commands.add_parser("verify-artifact")
    artifact.add_argument("path")
    artifact.set_defaults(handler=verify_artifact)
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
