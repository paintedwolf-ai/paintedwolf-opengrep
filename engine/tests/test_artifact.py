"""Artifact admission, atomic publication, and cross-process cache contracts."""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import importlib.util
import io
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

PACKAGE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("artifact", PACKAGE / "artifact.py")
ARTIFACT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ARTIFACT)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def signing_fixture(binary, profile=None):
    signing = ARTIFACT.signing_module()
    selected = signing.SigningProfile.parse(profile, platform="darwin")
    developer = selected.mode == "developer-id"
    inspection = {"schema_version": 1, "ok": True, "sha256": sha(binary), "bytes": len(binary),
        "slices": [{"architecture": "arm64", "cpu_type": 16777228, "cpu_subtype": 0,
            "identifier": "fixture", "team_id": selected.team_id,
            "certificate_sha256": selected.certificate_sha256,
            "secure_timestamp": "2026-09-08T00:00:00Z" if developer else None,
            "flags": 0x10000 if developer else 2, "entitlements": {}}]}
    image = {"path": "semgrep/bin/opengrep-core", **inspection}
    return {"profile": selected.record(), "profile_sha256": selected.digest(),
            "outer": inspection, "standalone": [image], "extracted": [image]}


class ArtifactTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.package = self.root / "package"
        self.package.mkdir()
        shutil.copyfile(PACKAGE / "build.py", self.package / "build.py")
        (self.package / "signing").mkdir()
        for name in ("signing.py", "native_signatures.m"):
            shutil.copyfile(PACKAGE / "signing" / name, self.package / "signing" / name)
        files = {"verify.py": "# frozen verifier\n", "source/tests/tainting/sample/flow.yaml": "rules: []\n",
                 "source/tests/tainting/sample/flow.js": "sink(source());\n",
                 "patches/series/0001-test.patch": "test patch\n", "locks/macos-arm64.opam.export": "test lock\n"}
        for name, raw in files.items():
            path = self.package / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(raw)
        write_json(self.package / "patches/series.json", {"format": 1, "patches": [
            {"id": "test", "target": "engine", "patch": "patches/series/0001-test.patch", "requires": []}]})
        write_json(self.package / "locks/runtimes.json", {"macos": {"deployment_target": "13.0"}})
        for name in ("native-file-selection", "callback-rule-validation", "model-rule-validation", "native-pattern-validation"):
            write_json(self.package / ("source/tests/" + name + ".json"), [])
        write_json(self.package / "source/tests/rule-translation.json", ["tainting/sample/flow.yaml"])
        self.lock = {"upstream_version": "1.29.0", "patch_version": 26, "revision": "a" * 40,
                     "interfaces_revision": "b" * 40, "grammars": [{"language": "sample", "generated_files": {
                         "parser.c": sha(b"parser"), "tree_sitter/parser.h": sha(b"header")}}], "files": {p.relative_to(self.package).as_posix(): sha(p.read_bytes())
                        for p in self.package.rglob("*") if p.is_file()}}
        write_json(self.package / "source-lock.json", self.lock)
        self.seed = self.root / "seed"
        self.seed.mkdir()
        self.binary = b"#!/bin/sh\nexit 0\n"
        (self.seed / "opengrep").write_bytes(self.binary)
        (self.seed / "opengrep").chmod(0o755)
        shutil.copyfile(self.package / "source-lock.json", self.seed / "source-lock.json")
        self.license = b"Reviewed source license\n"
        lock_hash = ARTIFACT.digest(self.package / "source-lock.json")
        self.archive_entries = {"engine/LICENSE": self.license, "engine/upstream.c": b"upstream source\n",
                                "third-party/dependency/source.tar.gz": b"retained corresponding source",
                                "engine/cli/LICENSE": {"symlink": "../LICENSE"},
                                "inputs/source-lock.json": (self.package / "source-lock.json").read_bytes(),
                                "engine/languages/native_scripts/sample/parser.c": b"parser",
                                "engine/languages/native_scripts/sample/include/tree_sitter/parser.h": b"header"}
        for name in self.lock["files"]:
            raw = (self.package / name).read_bytes()
            self.archive_entries["inputs/" + name] = raw
            if name.startswith("source/"):
                self.archive_entries["engine/" + name.removeprefix("source/")] = raw
        self.write_archive()
        execution = {"timed_out": False, "returncode": 0}
        self.rows = [{"case": name, "passed": True, "execution": execution, "exit_code": 0,
                      **({"translation_execution": {"discovery": execution, "translation": execution}}
                         if name.startswith("rule-translation/") else {})}
                     for name in sorted(ARTIFACT.expected_contracts(self.package))]
        self.rows.append({"contracts": len(self.rows), "failed": 0})
        self.write_rows()
        write_json(self.seed / "platform-checks.json", {"deployment_target": "13.0", "images": [
            {"path": "opengrep", "sha256": sha(self.binary), "architectures": ["arm64"],
             "deployment_versions": [[11, 0]], "dependencies": ["/usr/lib/libSystem.B.dylib"], "rpaths": []}]})
        write_json(self.seed / "runtime.json", {"environment": {"MACOSX_DEPLOYMENT_TARGET": "13.0"}})
        self.provenance = {"schema_version": 1, "version": "1.29.0+paintedwolf.26",
                           "upstream_revision": self.lock["revision"], "platform": "darwin", "architecture": "arm64",
                           "source_lock_sha256": lock_hash, "signing": signing_fixture(self.binary)}
        self.refresh_provenance()
        self.cache = self.root / "cache"

    def archive_manifest(self):
        return {"identity": {"source_lock_sha256": ARTIFACT.digest(self.package / "source-lock.json"),
                             "base_revision": self.lock["revision"], "interfaces_revision": self.lock["interfaces_revision"]},
                "files": {name: raw if isinstance(raw, dict) else {"bytes": len(raw), "sha256": sha(raw)}
                          for name, raw in self.archive_entries.items()}}

    def write_archive(self, manifest=None, extra=()):
        with tarfile.open(self.seed / "opengrep-source.tar.gz", "w:gz") as archive:
            entries = [*self.archive_entries.items(), *extra,
                       ("SOURCE-MANIFEST.json", json.dumps(manifest or self.archive_manifest()).encode())]
            for name, raw in entries:
                info = tarfile.TarInfo(name)
                if isinstance(raw, dict):
                    info.type, info.linkname = tarfile.SYMTYPE, raw["symlink"]
                    archive.addfile(info)
                else:
                    info.size = len(raw)
                    archive.addfile(info, io.BytesIO(raw))

    def write_rows(self):
        (self.seed / "contracts.jsonl").write_text("".join(json.dumps(row) + "\n" for row in self.rows))

    def refresh_provenance(self):
        for name, key in (("opengrep", "binary"), ("opengrep-source.tar.gz", "source_archive"),
                          ("contracts.jsonl", "contracts"), ("platform-checks.json", "platform_checks"), ("runtime.json", "runtime")):
            self.provenance[key + "_sha256"] = ARTIFACT.digest(self.seed / name)
            if key in ("binary", "source_archive"):
                self.provenance[key + "_bytes"] = (self.seed / name).stat().st_size
        write_json(self.seed / "provenance.json", self.provenance)

    def resolve(self, **kwargs):
        if "builder" in kwargs:
            original = kwargs["builder"]
            def builder(package, root, jobs, profile):
                self.addCleanup(shutil.rmtree, root.parent, True)
                return original(package, root, jobs, profile)
            kwargs["builder"] = builder
        return ARTIFACT.resolve(self.package, self.cache, target=("darwin", "arm64"), **kwargs)

    def assert_unpublished(self):
        self.assertEqual([p for p in self.cache.glob("*") if p.is_dir() and not p.name.startswith(".")], [])

    def test_seed_derives_license_and_cache_never_rebuilds(self):
        (self.seed / "additional-evidence.json").write_text("{}")
        result = self.resolve(seed=self.seed, no_build=True)
        self.assertTrue(result.is_absolute())
        self.assertEqual((result / "LICENSE").read_bytes(), self.license)
        self.assertTrue((result / "additional-evidence.json").is_file())
        self.assertFalse((self.seed / "LICENSE").exists())
        with mock.patch.object(ARTIFACT.subprocess, "run", side_effect=AssertionError("cache invoked builder")):
            self.assertEqual(result, self.resolve(no_build=True))

    def test_source_build_refuses_developer_id_before_launching_a_compiler(self):
        with mock.patch.object(ARTIFACT.subprocess, "Popen", side_effect=AssertionError("compiler started")):
            with self.assertRaisesRegex(ValueError, "compilation is ad-hoc"):
                ARTIFACT.build_artifact(self.package, self.root / "work", 2, {"mode": "developer-id"})

    def test_signing_profiles_do_not_share_cached_artifacts(self):
        adhoc = self.resolve(seed=self.seed)
        profile = {"schema_version": 1, "mode": "developer-id", "team_id": "ABCDEF1234",
                   "certificate_sha256": "a" * 64}
        with self.assertRaisesRegex(ValueError, "No qualified artifact"):
            self.resolve(signing_profile=profile, no_build=True)
        self.provenance["signing"] = signing_fixture(self.binary, profile)
        self.refresh_provenance()
        signing = ARTIFACT.signing_module()
        def compiler(path):
            path.write_bytes(b"test inspector")
            return path
        with mock.patch.object(signing, "compile_inspector", side_effect=compiler), \
             mock.patch.object(signing, "inspect_image", return_value=self.provenance["signing"]["outer"]) as inspector:
            developer = self.resolve(seed=self.seed, signing_profile=profile)
            self.assertNotEqual(adhoc, developer)
            inspector.reset_mock()
            self.assertEqual(developer, self.resolve(signing_profile=profile, no_build=True))
            inspector.assert_called_once()
        self.assertEqual(adhoc, self.resolve(no_build=True))
        with self.assertRaisesRegex(ValueError, "No qualified artifact"):
            self.resolve(signing_profile={**profile, "certificate_sha256": "b" * 64}, no_build=True)

    def test_unsigned_seed_cannot_satisfy_developer_profile(self):
        profile = {"schema_version": 1, "mode": "developer-id", "team_id": "ABCDEF1234",
                   "certificate_sha256": "a" * 64}
        signing = ARTIFACT.signing_module()
        with mock.patch.object(signing, "inspect_image") as inspector:
            with self.assertRaisesRegex(signing.SigningError, "requested profile"):
                self.resolve(seed=self.seed, signing_profile=profile)
            inspector.assert_not_called()
        self.assert_unpublished()

    def test_claimed_signing_requires_native_validation(self):
        profile = {"schema_version": 1, "mode": "developer-id", "team_id": "ABCDEF1234",
                   "certificate_sha256": "a" * 64}
        self.provenance["signing"] = signing_fixture(self.binary, profile)
        self.refresh_provenance()
        signing = ARTIFACT.signing_module()
        with mock.patch.object(signing, "compile_inspector"), \
             mock.patch.object(signing, "inspect_image", side_effect=signing.SigningError("invalid native signature")):
            with self.assertRaisesRegex(signing.SigningError, "invalid native signature"):
                self.resolve(seed=self.seed, signing_profile=profile)
        self.assert_unpublished()

    def test_missing_signing_inventory_is_refused(self):
        del self.provenance["signing"]
        self.refresh_provenance()
        with self.assertRaisesRegex(ARTIFACT.signing_module().SigningError, "signing record"):
            self.resolve(seed=self.seed)
        self.assert_unpublished()

    def test_cache_miss_no_build_does_not_invoke_builder(self):
        with self.assertRaisesRegex(ValueError, "No qualified artifact"):
            self.resolve(no_build=True, builder=lambda *_: self.fail("builder invoked"))
        self.assert_unpublished()

    def test_corrupt_cache_is_refused_without_automatic_rebuild(self):
        result = self.resolve(seed=self.seed)
        (result / "opengrep").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            self.resolve(builder=lambda *_: self.fail("corruption triggered rebuild"))

    def test_wrong_source_and_binary_size_are_refused(self):
        for field, value in (("source_lock_sha256", "0" * 64), ("binary_bytes", 999)):
            with self.subTest(field=field):
                old = self.provenance[field]
                self.provenance[field] = value
                write_json(self.seed / "provenance.json", self.provenance)
                with self.assertRaises(ValueError):
                    self.resolve(seed=self.seed)
                self.assert_unpublished()
                self.provenance[field] = old

    def test_provenance_identity_failure_names_the_mismatched_field(self):
        for field, value in (("schema_version", 2), ("version", "1.29.0+paintedwolf.25"),
                             ("upstream_revision", "0" * 40), ("source_lock_sha256", "0" * 64),
                             ("platform", "linux"), ("architecture", "x86_64")):
            with self.subTest(field=field):
                old = self.provenance[field]
                self.provenance[field] = value
                write_json(self.seed / "provenance.json", self.provenance)
                with self.assertRaisesRegex(ValueError, "identity differs: " + field + ": expected"):
                    self.resolve(seed=self.seed)
                self.assert_unpublished()
                self.provenance[field] = old

    def test_contract_failure_missing_duplicate_timeout_and_translation_are_refused(self):
        baseline = json.dumps(self.rows)
        changes = [lambda rows: rows[0].update(passed=False), lambda rows: rows.pop(0),
                   lambda rows: rows.insert(0, rows[0].copy()),
                   lambda rows: rows[0]["execution"].update(timed_out=True),
                   lambda rows: rows[0]["translation_execution"]["translation"].update(returncode=2),
                   lambda rows: rows[-1].update(contracts=999),
                   lambda rows: rows[0].update(expected=[1], actual=[2])]
        for change in changes:
            with self.subTest(change=change):
                self.rows = json.loads(baseline)
                change(self.rows)
                self.write_rows()
                self.refresh_provenance()
                with self.assertRaises(ValueError):
                    self.resolve(seed=self.seed)
                self.assert_unpublished()

    def test_changed_locked_source_is_refused_even_with_cached_artifact(self):
        self.resolve(seed=self.seed)
        (self.package / "source/tests/tainting/sample/flow.js").write_text("changed")
        with self.assertRaisesRegex(RuntimeError, "integrity mismatch"):
            self.resolve(no_build=True)

    def test_symlink_payload_and_wrong_license_are_refused(self):
        (self.seed / "outside").symlink_to(self.package / "build.py")
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.resolve(seed=self.seed)
        (self.seed / "outside").unlink()
        (self.seed / "LICENSE").write_bytes(b"different license")
        with self.assertRaisesRegex(ValueError, "license differs"):
            self.resolve(seed=self.seed)
        self.assert_unpublished()

    def test_platform_architecture_deployment_and_dependency_are_refused(self):
        path = self.seed / "platform-checks.json"
        baseline = path.read_text()
        for field, value in (("architectures", ["x86_64"]), ("deployment_versions", [[14, 0]]),
                             ("deployment_versions", [[13, -1]]), ("deployment_versions", [[True, 0]]),
                             ("dependencies", ["/opt/homebrew/lib/libx.dylib"]),
                             ("dependencies", ["/usr/lib/../../private/libx.dylib"]),
                             ("rpaths", ["/System/Library/../../private"]), ("sha256", "0" * 64)):
            with self.subTest(field=field):
                checks = json.loads(baseline)
                checks["images"][0][field] = value
                write_json(path, checks)
                self.refresh_provenance()
                with self.assertRaises(ValueError):
                    self.resolve(seed=self.seed)
                self.assert_unpublished()

    def test_equal_deployment_version_with_explicit_patch_component(self):
        path = self.seed / "platform-checks.json"
        checks = json.loads(path.read_text())
        checks["images"][0]["deployment_versions"] = [[13, 0, 0]]
        write_json(path, checks)
        self.refresh_provenance()
        self.resolve(seed=self.seed)

    def test_failed_build_never_publishes_partial_artifact(self):
        def builder(package, root, jobs, profile):
            self.assertFalse(root.exists())
            self.assertEqual(jobs, 2)
            root.mkdir()
            (root / "opengrep").write_bytes(b"unfinished")
            raise RuntimeError("build failed")
        with self.assertRaisesRegex(RuntimeError, "build failed"):
            self.resolve(builder=builder)
        self.assert_unpublished()

    def test_copy_corruption_is_detected_before_publication(self):
        original = shutil.copytree
        def corrupt(source, destination, **kwargs):
            result = original(source, destination, **kwargs)
            (destination / "opengrep").write_bytes(b"changed during copying")
            return result
        with mock.patch.object(ARTIFACT.shutil, "copytree", side_effect=corrupt):
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                self.resolve(seed=self.seed)
        self.assert_unpublished()

    def test_unqualified_build_output_is_never_published(self):
        def builder(package, root, jobs, profile):
            root.mkdir()
            shutil.copytree(self.seed, root / "artifact")
            report = root / "artifact/contracts.jsonl"
            report.write_text("{}\n")
            return root / "artifact"
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            self.resolve(builder=builder)
        self.assert_unpublished()

    def test_macos_build_location_is_independent_of_long_cache_path(self):
        self.cache = self.root / ("nested-checkout-" * 10) / "cache"
        observed = []
        def builder(package, root, jobs, profile):
            observed.append(root)
            self.assertEqual(root.parent.parent.resolve(), Path("/tmp").resolve())
            self.assertNotIn("build", root.resolve().parts)
            self.assertLess(len(str(root.resolve() / "runtime/Python.framework/Versions/3.13/Python")), 100)
            root.mkdir()
            shutil.copytree(self.seed, root / "artifact")
            return root / "artifact"
        result = self.resolve(builder=builder)
        self.assertTrue((result / "opengrep").is_file())
        self.assertFalse(observed[0].parent.exists())

    def test_archive_license_identity_is_checked_after_outer_digest(self):
        with tarfile.open(self.seed / "opengrep-source.tar.gz", "w:gz") as archive:
            raw = b"wrong license"
            info = tarfile.TarInfo("engine/LICENSE")
            info.size = len(raw)
            archive.addfile(info, io.BytesIO(raw))
        self.refresh_provenance()
        with self.assertRaisesRegex(ValueError, "archive identity or license missing"):
            self.resolve(seed=self.seed)
        self.assert_unpublished()

    def test_three_member_decoy_with_rewritten_manifest_is_refused(self):
        self.archive_entries = {name: raw for name, raw in self.archive_entries.items()
                                if name in ("engine/LICENSE", "inputs/source-lock.json")}
        self.write_archive()
        self.refresh_provenance()
        with self.assertRaisesRegex(ValueError, "locked input inventory differs"):
            self.resolve(seed=self.seed)
        self.assert_unpublished()

    def test_missing_or_altered_source_members_are_checked_against_manifest(self):
        baseline = self.archive_entries.copy()
        manifest = self.archive_manifest()
        for change in (lambda: self.archive_entries.pop("engine/upstream.c"),
                       lambda: self.archive_entries.update({"engine/upstream.c": b"changed source"})):
            with self.subTest(change=change):
                self.archive_entries = baseline.copy()
                change()
                self.write_archive(manifest=manifest)
                self.refresh_provenance()
                with self.assertRaisesRegex(ValueError, "members differ from source manifest"):
                    self.resolve(seed=self.seed)
                self.assert_unpublished()

    def test_rewritten_manifest_cannot_omit_or_alter_locked_inputs_and_installed_sources(self):
        baseline = self.archive_entries.copy()
        cases = [("inputs/build.py", None, "locked input inventory differs"),
                 ("inputs/build.py", b"changed builder", "locked input differs"),
                 ("engine/tests/tainting/sample/flow.js", None, "installed overlay differs"),
                 ("engine/tests/tainting/sample/flow.js", b"changed fixture", "installed overlay differs"),
                 ("engine/languages/native_scripts/sample/parser.c", None, "generated grammar differs"),
                 ("engine/languages/native_scripts/sample/include/tree_sitter/parser.h", b"changed header", "generated grammar differs")]
        for name, replacement, message in cases:
            with self.subTest(name=name, replacement=replacement):
                self.archive_entries = baseline.copy()
                if replacement is None:
                    self.archive_entries.pop(name)
                else:
                    self.archive_entries[name] = replacement
                self.write_archive()
                self.refresh_provenance()
                with self.assertRaisesRegex(ValueError, message):
                    self.resolve(seed=self.seed)
                self.assert_unpublished()

    def test_source_archive_rejects_special_members_and_symlink_payloads(self):
        for kind, size in ((tarfile.DIRTYPE, 0), (tarfile.LNKTYPE, 0), (tarfile.FIFOTYPE, 0), (tarfile.SYMTYPE, 1)):
            with self.subTest(kind=kind, size=size):
                with tarfile.open(self.seed / "opengrep-source.tar.gz", "w:gz") as archive:
                    member = tarfile.TarInfo("engine/invalid")
                    member.type, member.size, member.linkname = kind, size, "LICENSE"
                    archive.addfile(member, io.BytesIO(b"x") if size else None)
                self.refresh_provenance()
                with self.assertRaisesRegex(ValueError, "Non-file source archive member|symlink has a data payload"):
                    self.resolve(seed=self.seed)
                self.assert_unpublished()

    def test_manifest_member_sizes_require_integers(self):
        manifest = self.archive_manifest()
        manifest["files"]["engine/LICENSE"]["bytes"] = float(len(self.license))
        self.write_archive(manifest=manifest)
        self.refresh_provenance()
        with self.assertRaisesRegex(ValueError, "Invalid source manifest member schema"):
            self.resolve(seed=self.seed)

    def test_archive_paths_duplicate_members_and_escaping_links_are_refused(self):
        baseline = self.archive_entries.copy()
        for name, raw in (("../escape", b"source"), ("engine/./alias", b"source"),
                          ("engine/link", {"symlink": "../../escape"}),
                          ("engine/link", {"symlink": "/absolute"})):
            with self.subTest(name=name, raw=raw):
                self.archive_entries = {**baseline, name: raw}
                self.write_archive()
                self.refresh_provenance()
                with self.assertRaisesRegex(ValueError, "Invalid source archive"):
                    self.resolve(seed=self.seed)
                self.assert_unpublished()
        self.archive_entries = baseline
        self.write_archive(extra=[("engine/LICENSE", self.license)])
        self.refresh_provenance()
        with self.assertRaisesRegex(ValueError, "Duplicate source archive member"):
            self.resolve(seed=self.seed)

    def test_concurrent_resolvers_build_once_and_observe_complete_artifact(self):
        context = multiprocessing.get_context("fork")
        started, release = context.Event(), context.Event()
        results = context.Queue()
        marker = self.root / "build-count"
        def builder(package, root, jobs, profile):
            with marker.open("a") as output:
                output.write("build\n")
            started.set()
            if not release.wait(120):
                raise RuntimeError("test did not release builder")
            root.mkdir()
            shutil.copytree(self.seed, root / "artifact")
            return root / "artifact"
        def worker():
            try:
                path = self.resolve(builder=builder)
                results.put((str(path), (path / "LICENSE").read_bytes()))
            except Exception as error:
                results.put(("error", repr(error)))
        processes = [context.Process(target=worker) for _ in range(2)]
        try:
            for process in processes:
                process.start()
            self.assertTrue(started.wait(120), "builder did not start")
            self.assert_unpublished()
            release.set()
            outcomes = [results.get(timeout=120) for _ in processes]
            self.assertEqual(outcomes[0], outcomes[1])
            self.assertNotEqual(outcomes[0][0], "error", outcomes)
            self.assertEqual(outcomes[0][1], self.license)
            self.assertEqual(marker.read_text(), "build\n")
        finally:
            release.set()
            for process in processes:
                process.join(120)
                if process.is_alive():
                    process.terminate()
                    process.join()
            results.close()

    def test_waiters_do_not_repeat_failed_build_and_explicit_retry_recovers(self):
        context = multiprocessing.get_context("fork")
        started, release = context.Event(), context.Event()
        results = context.Queue()
        marker = self.root / "failed-build-count"
        def builder(package, root, jobs, profile):
            with marker.open("a") as output:
                output.write("build\n")
            root.mkdir()
            (root / "diagnostic.txt").write_text("compiler failed")
            started.set()
            if not release.wait(120):
                raise RuntimeError("test did not release builder")
            raise RuntimeError("compiler failed")
        def worker():
            try:
                self.resolve(builder=builder)
                results.put("unexpected success")
            except Exception as error:
                results.put(str(error))
        processes = [context.Process(target=worker) for _ in range(2)]
        try:
            for process in processes:
                process.start()
            self.assertTrue(started.wait(120), "builder did not start")
            release.set()
            outcomes = [results.get(timeout=120) for _ in processes]
            self.assertTrue(all("compiler failed" in outcome for outcome in outcomes), outcomes)
            self.assertTrue(any("--retry-failed" in outcome for outcome in outcomes), outcomes)
            self.assertEqual(marker.read_text(), "build\n")
            failures = list(self.cache.glob("*.failed.json"))
            self.assertEqual(len(failures), 1)
            failed = json.loads(failures[0].read_text())
            self.assertEqual((Path(failed["build_directory"]) / "work/diagnostic.txt").read_text(), "compiler failed")
            with self.assertRaisesRegex(ValueError, "Previous source build failed"):
                self.resolve(builder=lambda *_: self.fail("failure retried implicitly"))
            def successful(package, root, jobs, profile):
                root.mkdir()
                shutil.copytree(self.seed, root / "artifact")
                return root / "artifact"
            installed = self.resolve(builder=successful, retry_failed=True)
            self.assertEqual((installed / "LICENSE").read_bytes(), self.license)
            self.assertFalse(failures[0].exists())
        finally:
            release.set()
            for process in processes:
                process.join(120)
                if process.is_alive():
                    process.terminate()
                    process.join()
            results.close()

    def test_explicit_seed_recovers_a_failed_build(self):
        with self.assertRaisesRegex(RuntimeError, "failed"):
            self.resolve(builder=mock.Mock(side_effect=RuntimeError("failed")))
        installed = self.resolve(seed=self.seed, no_build=True)
        self.assertEqual((installed / "LICENSE").read_bytes(), self.license)
        self.assertEqual(list(self.cache.glob("*.failed.json")), [])

    def test_cli_stdout_is_only_the_absolute_directory(self):
        output = io.StringIO()
        with mock.patch.object(ARTIFACT, "PACKAGE", self.package), mock.patch.object(ARTIFACT, "native_target", return_value=("darwin", "arm64")), \
             mock.patch("sys.argv", ["artifact.py", "--seed", str(self.seed), "--cache-dir", str(self.cache), "--no-build"]), redirect_stdout(output):
            self.assertEqual(ARTIFACT.main(), 0)
        lines = output.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertTrue(Path(lines[0]).is_absolute())
        self.assertTrue((Path(lines[0]) / "LICENSE").is_file())

    def test_snapshot_cli_reuses_shared_cache_and_checks_snapshot_inputs(self):
        installed = self.resolve(seed=self.seed, no_build=True)
        snapshot = self.root / "snapshot/engine"
        shutil.copytree(self.package, snapshot)
        output, diagnostic = io.StringIO(), io.StringIO()
        with mock.patch.object(ARTIFACT, "PACKAGE", snapshot), \
             mock.patch.object(ARTIFACT, "native_target", return_value=("darwin", "arm64")), \
             mock.patch.dict(os.environ, {"OPENGREP_CACHE_DIR": str(self.cache), "OPENGREP_SIGNING_PROFILE": ""}), \
             mock.patch("sys.argv", ["artifact.py", "--no-build"]), redirect_stdout(output), redirect_stderr(diagnostic):
            self.assertEqual(ARTIFACT.main(), 0)
            self.assertEqual(output.getvalue(), str(installed) + "\n")
            self.assertFalse((snapshot.parent / ".cache").exists())
            verifier = snapshot / "verify.py"
            original = verifier.read_bytes()
            verifier.write_bytes(original + b"# unreviewed change\n")
            self.assertEqual(ARTIFACT.main(), 1)
            self.assertIn("Source package integrity mismatch: verify.py", diagnostic.getvalue())
            verifier.write_bytes(original)
            diagnostic.seek(0)
            diagnostic.truncate()
            with (snapshot / "source-lock.json").open("a") as changed:
                changed.write("\n")
            self.assertEqual(ARTIFACT.main(), 1)
            self.assertIn("No qualified artifact is cached", diagnostic.getvalue())
        self.assertEqual((installed / "opengrep").read_bytes(), self.binary)

    def test_explicit_cache_directory_overrides_environment(self):
        installed = self.resolve(seed=self.seed, no_build=True)
        unused = self.root / "unused-environment-cache"
        output = io.StringIO()
        with mock.patch.object(ARTIFACT, "PACKAGE", self.package), \
             mock.patch.object(ARTIFACT, "native_target", return_value=("darwin", "arm64")), \
             mock.patch.dict(os.environ, {"OPENGREP_CACHE_DIR": str(unused), "OPENGREP_SIGNING_PROFILE": ""}), \
             mock.patch("sys.argv", ["artifact.py", "--cache-dir", str(self.cache), "--no-build"]), redirect_stdout(output):
            self.assertEqual(ARTIFACT.main(), 0)
        self.assertEqual(output.getvalue(), str(installed) + "\n")
        self.assertFalse(unused.exists())

    @unittest.skipUnless(sys.platform == "darwin" and __import__("platform").machine() == "arm64",
                         "The qualified subprocess fixture targets native macOS arm64")
    def test_native_cli_reuses_shared_environment_cache(self):
        installed = self.resolve(seed=self.seed, no_build=True)
        checkout = self.root / "snapshot"
        package = checkout / "engine"
        shutil.copytree(self.package, package)
        shutil.copyfile(PACKAGE / "artifact.py", package / "artifact.py")
        shutil.copytree(PACKAGE / "signing", package / "signing", dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("release-profile.json"))
        result = subprocess.run([sys.executable, str(package / "artifact.py"), "--no-build"], cwd=checkout,
            env={**os.environ, "OPENGREP_CACHE_DIR": str(self.cache), "OPENGREP_SIGNING_PROFILE": ""},
            capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, str(installed) + "\n")
        self.assertFalse((checkout / ".cache").exists())


if __name__ == "__main__":
    unittest.main()
