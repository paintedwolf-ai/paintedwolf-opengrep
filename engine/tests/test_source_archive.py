import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "source_archive", Path(__file__).parents[1] / "build_support/source_archive.py")
ARCHIVE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ARCHIVE)


class SourceArchiveTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source.ml"
        self.source.write_bytes(b"modified implementation\n")
        self.entries = {"engine/source.ml": self.source}

    def create(self, name="source.tar.gz"):
        output = self.root / name
        ARCHIVE.archive_sources(output, self.entries, {"base_revision": "pinned"}, [self.root])
        return output

    def test_archive_contains_modified_bytes_and_normalized_identity(self):
        first = self.create()
        self.source.touch()
        second = self.create("second.tar.gz")
        self.assertEqual(first.read_bytes(), second.read_bytes())
        with tarfile.open(first) as archive:
            self.assertEqual(archive.extractfile("engine/source.ml").read(), self.source.read_bytes())
            entry = archive.getmember("engine/source.ml")
            self.assertEqual((entry.uid, entry.gid, entry.mtime), (0, 0, 0))
            manifest = json.load(archive.extractfile("SOURCE-MANIFEST.json"))
            self.assertEqual(manifest["files"]["engine/source.ml"]["sha256"],
                             hashlib.sha256(self.source.read_bytes()).hexdigest())

    def test_build_outputs_outside_the_source_inventory_are_excluded(self):
        (self.root / "opengrep-core").write_bytes(b"compiled binary")
        with tarfile.open(self.create()) as archive:
            self.assertEqual(archive.getnames(), ["engine/source.ml", "SOURCE-MANIFEST.json"])

    def test_relative_source_link_is_preserved(self):
        link = self.root / "alias.ml"
        link.symlink_to("source.ml")
        self.entries["engine/alias.ml"] = link
        with tarfile.open(self.create()) as archive:
            entry = archive.getmember("engine/alias.ml")
            self.assertTrue(entry.issym())
            self.assertEqual(entry.linkname, "source.ml")

    def test_relative_link_to_a_build_output_is_preserved(self):
        link = self.root / "alias.ml"
        link.symlink_to("_build/output")
        self.entries = {"engine/alias.ml": link}
        with tarfile.open(self.create()) as archive:
            self.assertEqual(archive.getmember("engine/alias.ml").linkname, "_build/output")

    def test_relative_link_cannot_escape_extraction_root(self):
        link = self.root / "alias.ml"
        link.symlink_to("../../outside")
        self.entries = {"engine/alias.ml": link}
        with self.assertRaisesRegex(RuntimeError, "Invalid source archive path"):
            self.create()

    def test_absolute_source_link_is_rejected(self):
        link = self.root / "alias.ml"
        link.symlink_to(self.source)
        self.entries["engine/alias.ml"] = link
        with self.assertRaisesRegex(RuntimeError, "Absolute symlink"):
            self.create()

    def test_archive_path_cannot_escape_extraction_root(self):
        self.entries = {"../outside.ml": self.source}
        with self.assertRaisesRegex(RuntimeError, "Invalid source archive path"):
            self.create()

    def test_grammar_patch_additions_are_archived_without_untracked_probes(self):
        engine = self.root / "engine"
        grammar = self.root / "grammar-example"
        package = self.root / "inputs"
        for tree in (engine, grammar):
            tree.mkdir()
            subprocess.run(["git", "init", "--quiet", str(tree)], check=True)
        (grammar / "grammar.js").write_text("original grammar\n")
        (grammar / "removed.test").write_text("removed case\n")
        subprocess.run(["git", "add", "grammar.js", "removed.test"], cwd=grammar, check=True)
        (grammar / "grammar.js").write_text("modified grammar\n")
        (grammar / "removed.test").unlink()
        (grammar / "new.test").write_text("new regression\n")
        (grammar / "probe.test").write_text("private probe\n")
        (package / "patches").mkdir(parents=True)
        (package / "patches/series.json").write_text('{"patches": []}\n')
        (package / "patches/grammar.patch").write_text(
            "--- a/grammar.js\n+++ b/grammar.js\n@@ -1 +1 @@\n"
            "-original grammar\n+modified grammar\n"
            "--- a/removed.test\n+++ /dev/null\n@@ -1 +0,0 @@\n-removed case\n"
            "--- /dev/null\n+++ b/new.test\n@@ -0,0 +1 @@\n+new regression\n")
        lock = {"files": {}, "grammars": [{"language": "example",
                "patch": "patches/grammar.patch", "generated_files": {}}]}
        (package / "source-lock.json").write_text(json.dumps(lock))
        self.entries = ARCHIVE.source_entries(self.root, package, lock)
        with tarfile.open(self.create()) as archive:
            self.assertEqual(archive.extractfile("grammars/example/new.test").read(),
                             b"new regression\n")
            self.assertEqual(archive.extractfile("grammars/example/grammar.js").read(),
                             b"modified grammar\n")
            self.assertNotIn("grammars/example/removed.test", archive.getnames())
            self.assertNotIn("grammars/example/probe.test", archive.getnames())

    def engine_with_submodule(self, name, path, filename):
        """An engine tree whose index records `path` as a checked-out submodule."""
        engine = self.root / name
        engine.mkdir()
        subprocess.run(["git", "init", "--quiet", str(engine)], check=True)
        (engine / "compiled.ml").write_text("engine source\n")
        subprocess.run(["git", "add", "compiled.ml"], cwd=engine, check=True)
        nested = engine / path
        nested.mkdir(parents=True)
        subprocess.run(["git", "init", "--quiet", str(nested)], check=True)
        (nested / filename).write_text("submodule content\n")
        subprocess.run(["git", "add", filename], cwd=nested, check=True)
        subprocess.run(["git", "-c", "user.email=t@e", "-c", "user.name=t",
                        "commit", "--quiet", "-m", "content"], cwd=nested, check=True)
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=nested, text=True).strip()
        subprocess.run(["git", "update-index", "--add", "--cacheinfo",
                        f"160000,{revision},{path}"], cwd=engine, check=True)
        return engine

    def test_test_corpus_submodules_are_not_archived(self):
        # A fixture corpus compiles into nothing and carries its own terms —
        # semgrep-rules is LGPL-2.1 with a Commons Clause condition — so the
        # archive skips it instead of walking it.
        engine = self.engine_with_submodule("corpus-engine", "tests/semgrep-rules", "rule.yaml")
        self.assertEqual([path.name for path in ARCHIVE.tracked_sources(engine)], ["compiled.ml"])

    def test_library_submodules_are_still_walked(self):
        # The exclusion is narrow: a submodule outside a test tree is source of
        # the work and its files stay in the archive.
        engine = self.engine_with_submodule("library-engine", "libs/linked", "library.ml")
        self.assertEqual(sorted(path.name for path in ARCHIVE.tracked_sources(engine)),
                         ["compiled.ml", "library.ml"])

    def test_retained_third_party_sources_are_archived_under_their_own_prefix(self):
        retained = self.root / "third-party"
        (retained / "native_gmp").mkdir(parents=True)
        (retained / "native_gmp/gmp-6.3.0.tar.xz").write_bytes(b"gmp source archive")
        (retained / "RETAINED-SOURCE.json").write_text('{"retained": []}\n')
        entries = ARCHIVE.third_party_entries(retained)
        self.assertEqual(sorted(entries), ["third-party/RETAINED-SOURCE.json",
                                           "third-party/native_gmp/gmp-6.3.0.tar.xz"])
        self.entries.update(entries)
        with tarfile.open(self.create()) as archive:
            self.assertEqual(
                archive.extractfile("third-party/native_gmp/gmp-6.3.0.tar.xz").read(),
                b"gmp source archive")

    def test_patch_inventory_cannot_escape_source_root(self):
        for name in ("../outside", "/outside"):
            with self.subTest(name=name), patch.object(
                    ARCHIVE.subprocess, "check_output", return_value=f"1\t0\t{name}\0".encode()):
                with self.assertRaisesRegex(RuntimeError, "Invalid source archive path"):
                    list(ARCHIVE.patch_sources(self.root, self.root / "grammar.patch"))


if __name__ == "__main__":
    unittest.main()
