import hashlib
import importlib.util
import json
from pathlib import Path
import py_compile
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


SPEC = importlib.util.spec_from_file_location("opengrep_build", Path(__file__).parents[1] / "build.py")
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


class PackageSnapshotTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.package = self.root / "package"
        self.package.mkdir()
        self.destination = self.root / "snapshot"
        series = {"format": 1, "patches": [{"id": "model", "target": "engine", "patch": "patches/series/0001-model.patch", "requires": []}]}
        files = {"build.py": b"build", "verify.py": b"verify", "source/model.ml": b"model",
                 "patches/series/0001-model.patch": b"patch", "patches/series.json": json.dumps(series).encode(),
                 "locks/python.txt": b"dependencies"}
        for relative, raw in files.items():
            path = self.package / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        self.lock = {"files": {relative: hashlib.sha256(raw).hexdigest() for relative, raw in files.items()}}
        (self.package / "source-lock.json").write_text(json.dumps(self.lock))

    def test_later_edits_do_not_change_build_inputs(self):
        captured = BUILD.snapshot_package(self.package, self.destination)
        (self.package / "source/model.ml").write_bytes(b"changed")
        (self.package / "source/added.ml").write_bytes(b"new")
        (self.package / "source-lock.json").write_text("{}")
        self.assertEqual(captured, self.lock)
        self.assertEqual((self.destination / "source/model.ml").read_bytes(), b"model")
        self.assertFalse((self.destination / "source/added.ml").exists())
        self.assertEqual(json.loads((self.destination / "source-lock.json").read_bytes()), self.lock)

    def test_unlocked_input_is_rejected(self):
        (self.package / "source/added.ml").write_bytes(b"new")
        with self.assertRaisesRegex(RuntimeError, "inventory mismatch"):
            BUILD.snapshot_package(self.package, self.destination)

    def test_python_cache_does_not_change_build_inputs(self):
        support = self.package / "build_support" / "runner.py"
        support.parent.mkdir()
        support.write_text("value = 1\n")
        self.lock["files"]["build_support/runner.py"] = hashlib.sha256(support.read_bytes()).hexdigest()
        (self.package / "source-lock.json").write_text(json.dumps(self.lock))
        py_compile.compile(str(support), cfile=str(support.parent / "__pycache__/runner.pyc"), doraise=True)
        self.assertTrue((support.parent / "__pycache__").exists())
        self.assertEqual(BUILD.snapshot_package(self.package, self.destination), self.lock)
        self.assertFalse((self.destination / "build_support/__pycache__").exists())

    def test_python_cache_cannot_be_a_locked_input(self):
        cache = self.package / "build_support/__pycache__/runner.cpython-313.pyc"
        cache.parent.mkdir(parents=True)
        cache.write_bytes(b"cache")
        self.lock["files"][cache.relative_to(self.package).as_posix()] = hashlib.sha256(cache.read_bytes()).hexdigest()
        (self.package / "source-lock.json").write_text(json.dumps(self.lock))
        with self.assertRaisesRegex(RuntimeError, "inventory mismatch"):
            BUILD.snapshot_package(self.package, self.destination)

    def test_missing_input_is_rejected(self):
        (self.package / "verify.py").unlink()
        with self.assertRaisesRegex(RuntimeError, "inventory mismatch"):
            BUILD.snapshot_package(self.package, self.destination)

    def test_modified_input_is_rejected(self):
        (self.package / "source/model.ml").write_bytes(b"changed")
        with self.assertRaisesRegex(RuntimeError, "integrity mismatch"):
            BUILD.snapshot_package(self.package, self.destination)

    def test_symlinked_source_directory_is_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "injected.ml").write_bytes(b"unlocked")
        (self.package / "source/link").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, "symlink"):
            BUILD.snapshot_package(self.package, self.destination)

    def test_dependency_cannot_be_applied_after_its_consumer(self):
        path = self.package / "patches/series.json"
        series = json.loads(path.read_text())
        series["patches"][0]["requires"] = ["later-foundation"]
        path.write_text(json.dumps(series))
        with self.assertRaisesRegex(RuntimeError, "dependency must precede"):
            BUILD.patch_series(self.package)

    def test_unlisted_patch_cannot_be_omitted_from_build(self):
        (self.package / "patches/series/0002-missing.patch").write_text("patch")
        with self.assertRaisesRegex(RuntimeError, "unlisted patches"):
            BUILD.patch_series(self.package)

    def test_patch_target_must_name_a_locked_checkout(self):
        path = self.package / "patches/series.json"
        series = json.loads(path.read_text())
        series["patches"][0]["target"] = "../other-project"
        path.write_text(json.dumps(series))
        with self.assertRaisesRegex(RuntimeError, "Invalid or duplicate"):
            BUILD.patch_series(self.package)

    def test_duplicate_patch_cannot_be_applied_twice(self):
        path = self.package / "patches/series.json"
        series = json.loads(path.read_text())
        series["patches"].append(dict(series["patches"][0], id="duplicate"))
        path.write_text(json.dumps(series))
        with self.assertRaisesRegex(RuntimeError, "Invalid or duplicate"):
            BUILD.patch_series(self.package)


class GrammarPatchTest(unittest.TestCase):
    def test_unmodified_grammar_needs_no_patch(self):
        self.assertIsNone(BUILD.grammar_patch(Path("unused"), {"patch": None}))

    def test_declared_patch_is_used_exactly(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory)
            patch = package / "patches" / "reader.patch"
            patch.parent.mkdir()
            patch.write_text("patch")
            self.assertEqual(BUILD.grammar_patch(package, {"patch": "patches/reader.patch"}), patch)
            for invalid in ("../reader.patch", "/tmp/reader.patch", "patches/missing.patch",
                            "patches/../reader.patch", "patches/reader.txt"):
                with self.subTest(path=invalid), self.assertRaisesRegex(RuntimeError, "Invalid grammar patch"):
                    BUILD.grammar_patch(package, {"patch": invalid})


class BuildVersionTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "engine"
        self.lock = {"upstream_version": "1.30.0", "patch_version": 32,
                     "upstream": "unused", "revision": "revision",
                     "interfaces_revision": "interfaces", "grammars": []}
        self.original = {
            "cli/setup.py": 'setuptools.setup(\n    version="1.30.0",\n)\n',
            "cli/src/semgrep/__init__.py": '__VERSION__ = "1.30.0"\n__SEMGREP_VERSION__ = "1.100.0"\n',
            "src/core/Version.ml": 'let version = "1.30.0"\nlet version_semgrep = "1.100.0"\n',
        }
        self.write_original()

    def write_original(self):
        for relative, text in self.original.items():
            path = self.source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)

    def test_future_revisions_stamp_every_runtime_and_metadata_version(self):
        for revision in (32, 33, 147):
            with self.subTest(revision=revision):
                self.write_original()
                lock = dict(self.lock, patch_version=revision)
                BUILD.stamp_version(self.source, lock)
                for relative, text in self.original.items():
                    self.assertEqual((self.source / relative).read_text(),
                                     text.replace('"1.30.0"', f'"1.30.0+paintedwolf.{revision}"'))

    def test_changed_or_duplicate_declaration_rejects_before_any_write(self):
        last = self.source / "src/core/Version.ml"
        for text in ('let version = "1.31.0"\n', 'let version = "1.30.0"\n' * 2,
                     'let release = "1.30.0"\n'):
            with self.subTest(declaration=text):
                self.write_original()
                last.write_text(text)
                before = {path: path.read_bytes() for path in self.source.rglob("*") if path.is_file()}
                with self.assertRaisesRegex(RuntimeError, "Unexpected upstream version declaration"):
                    BUILD.stamp_version(self.source, self.lock)
                self.assertEqual({path: path.read_bytes() for path in before}, before)

    def test_invalid_lock_version_is_not_written_into_source(self):
        for field, value in (("patch_version", True), ("patch_version", "32"),
                             ("patch_version", 0), ("upstream_version", '1.30.0"; code'),
                             ("upstream_version", "01.30.0")):
            with self.subTest(field=field, value=value), self.assertRaisesRegex(RuntimeError, "Invalid locked"):
                BUILD.stamp_version(self.source, dict(self.lock, **{field: value}))
        for relative, text in self.original.items():
            self.assertEqual((self.source / relative).read_text(), text)

    def test_prepare_stamps_after_overlay_before_returning_archivable_source(self):
        package = self.root / "package"
        with mock.patch.object(BUILD, "checkout"), mock.patch.object(BUILD, "run"), \
                mock.patch.object(BUILD, "patch_series", return_value=[]), \
                mock.patch.object(BUILD.subprocess, "check_output", return_value="interfaces\n"), \
                mock.patch.object(BUILD.shutil, "copytree", side_effect=lambda *args, **kwargs: self.write_original()):
            source = BUILD.prepare(self.root, package, self.lock)
        self.assertEqual(source, self.source)
        for relative in self.original:
            self.assertIn('"1.30.0+paintedwolf.32"', (source / relative).read_text())

    def test_stale_executable_fails_before_contracts_and_matching_version_runs_them(self):
        package = self.root / "package"
        dependency = package / "locks/linux-arm64.opam.export"
        dependency.parent.mkdir(parents=True)
        dependency.write_text("dependencies")
        (package / "source-lock.json").write_text(json.dumps(self.lock))
        compiled = self.source / "_build/default/src/main/Main.exe"
        compiled.parent.mkdir(parents=True)
        compiled.write_bytes(b"native core")
        (self.source / "cli/src/semgrep/bin").mkdir()
        profile = SimpleNamespace(mode="adhoc", digest=lambda: "profile")
        for reported, success in (("1.30.0+paintedwolf.30\n", False),
                                  ("1.30.0+paintedwolf.32\n", True)):
            with self.subTest(reported=reported), \
                    mock.patch.object(BUILD.platform, "system", return_value="Linux"), \
                    mock.patch.object(BUILD.platform, "machine", return_value="aarch64"), \
                    mock.patch.object(BUILD.subprocess, "run") as commands, \
                    mock.patch.object(BUILD.subprocess, "check_output", return_value=reported):
                if success:
                    result = BUILD.build(self.root, package, self.source, self.lock, 2, "python", None, profile)
                    self.assertEqual(result["version"], reported.strip())
                else:
                    with self.assertRaisesRegex(RuntimeError, "Built engine version mismatch"):
                        BUILD.build(self.root, package, self.source, self.lock, 2, "python", None, profile)
                contracts = [call for call in commands.call_args_list
                             if str(package / "verify.py") in call.args[0]]
                self.assertEqual(len(contracts), int(success))
                self.assertEqual((self.root / "contracts.jsonl").exists(), success)


if __name__ == "__main__":
    unittest.main()
