import gzip
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


PACKAGE = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("dependencies", PACKAGE / "build_support/dependencies.py")
DEPS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DEPS)


def distribution(data=b"reviewed distribution", filename="package.whl"):
    return {"filename": filename, "url": "https://example.test/" + filename,
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


class DependencyFetchTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def response(self, data):
        opener = mock.Mock()
        opener.open.return_value = io.BytesIO(data)
        return mock.patch.object(DEPS.urllib.request, "build_opener", return_value=opener)

    def test_download_is_published_only_after_hash_validation(self):
        data = b"reviewed distribution"
        with self.response(data):
            target = DEPS.fetch(distribution(data), self.root)
        self.assertEqual(target.read_bytes(), data)
        self.assertEqual(list(self.root.iterdir()), [target])
        with mock.patch.object(DEPS.urllib.request, "build_opener") as network:
            self.assertEqual(DEPS.fetch(distribution(data), self.root, offline=True), target)
        network.assert_not_called()

    def test_wrong_hash_truncation_and_overrun_leave_no_file(self):
        expected = b"reviewed distribution"
        for data in (b"x" * len(expected), expected[:-1], expected + b"extra"):
            with self.subTest(data=data), self.response(data):
                with self.assertRaises(RuntimeError):
                    DEPS.fetch(distribution(expected), self.root)
                self.assertEqual(list(self.root.iterdir()), [])

    def test_corrupt_cache_is_rejected_without_refetch(self):
        pin = distribution()
        (self.root / pin["filename"]).write_bytes(b"x" * pin["bytes"])
        with mock.patch.object(DEPS.urllib.request, "build_opener") as network:
            with self.assertRaisesRegex(RuntimeError, "SHA-256 mismatch"):
                DEPS.fetch(pin, self.root)
        network.assert_not_called()

    def test_symlink_cache_is_rejected(self):
        original = self.root / "original"
        original.write_bytes(b"reviewed distribution")
        (self.root / "package.whl").symlink_to(original)
        with self.assertRaisesRegex(RuntimeError, "file type mismatch"):
            DEPS.fetch(distribution(), self.root)

    def test_offline_miss_never_uses_network(self):
        with mock.patch.object(DEPS.urllib.request, "build_opener") as network:
            with self.assertRaisesRegex(RuntimeError, "unavailable offline"):
                DEPS.fetch(distribution(), self.root, offline=True)
        network.assert_not_called()

    def test_unsafe_url_filename_or_hash_is_rejected_before_network(self):
        for field, value in (("filename", "../escape"), ("filename", "/tmp/escape"),
                             ("url", "http://example.test/file"), ("url", "https://user:password@example.test/file"),
                             ("bytes", DEPS.MAX_DISTRIBUTION_BYTES + 1), ("bytes", True), ("sha256", "bad")):
            with self.subTest(field=field), mock.patch.object(DEPS.urllib.request, "build_opener") as network:
                with self.assertRaises(ValueError):
                    DEPS.fetch(dict(distribution(), **{field: value}), self.root)
                network.assert_not_called()

    def test_redirect_cannot_downgrade_to_http(self):
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            DEPS.HTTPSRedirects().redirect_request(None, None, 302, "", {}, "http://example.test/file")

    def test_generator_checks_compressed_and_executable_identities(self):
        data = b"reviewed executable"
        archive = gzip.compress(data, mtime=0)
        pin = dict(distribution(archive, "tree-sitter.gz"), executable_sha256=hashlib.sha256(data).hexdigest(),
                   executable_bytes=len(data))
        lock = {"generators": {"tree-sitter-cli@0.27.0": {"macos-arm64": pin}}}
        with mock.patch.object(DEPS, "read_lock", return_value=lock), self.response(archive):
            path = DEPS.grammar_generator(PACKAGE, self.root, "tree-sitter-cli@0.27.0", "macos-arm64")
            self.assertEqual(path.read_bytes(), data)
            self.assertEqual(path.stat().st_mode & 0o777, 0o755)
            path.write_bytes(b"x" * len(data))
            with self.assertRaisesRegex(RuntimeError, "SHA-256 mismatch"):
                DEPS.grammar_generator(PACKAGE, self.root, "tree-sitter-cli@0.27.0", "macos-arm64")

    def test_generator_wrong_expanded_hash_or_size_is_never_published(self):
        data = b"reviewed executable"
        archive = gzip.compress(data, mtime=0)
        pin = dict(distribution(archive, "tree-sitter.gz"), executable_sha256="0" * 64,
                   executable_bytes=len(data))
        for pin in (pin, dict(pin, executable_bytes=2)):
            lock = {"generators": {"generator": {"platform": pin}}}
            with self.subTest(pin=pin), mock.patch.object(DEPS, "read_lock", return_value=lock), self.response(archive):
                with self.assertRaises(RuntimeError):
                    DEPS.grammar_generator(PACKAGE, self.root, "generator", "platform")
                self.assertFalse((self.root / "tree-sitter").exists())
                self.assertEqual(list(self.root.glob(".generator-*")), [])


class PythonDependencyTest(unittest.TestCase):
    def test_licensing_enumerates_exact_bootstrap_artifacts_as_build_only(self):
        spec = importlib.util.spec_from_file_location("dependency_license_sources", PACKAGE / "licensing/sources.py")
        sources = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sources)
        components = sources.enumerate_components()["python_packages"]
        bootstrap = {entry["name"]: entry for entry in components if entry["linkage"] == "build-only"}
        self.assertEqual(set(bootstrap), {"pip", "setuptools", "wheel"})
        for pin in DEPS.python_distributions(PACKAGE)["bootstrap"]:
            for key, value in pin.items():
                self.assertEqual(bootstrap[pin["name"]][key], value)
        self.assertTrue(all(entry["linkage"] == "bundled" for entry in components
                            if entry["name"] not in bootstrap))

    def test_every_locked_requirement_matches_a_distribution_hash(self):
        spec = DEPS.python_distributions(PACKAGE)
        self.assertEqual(len(spec["runtime"]), 38)
        self.assertEqual({entry["name"] for entry in spec["bootstrap"]}, {"pip", "setuptools", "wheel"})
        for entry in spec["runtime"] + spec["bootstrap"]:
            self.assertTrue(entry["url"].startswith("https://files.pythonhosted.org/"))

    def test_lock_drift_rejects_installation(self):
        lock = DEPS.read_lock(PACKAGE)
        lock["python"][DEPS.PYTHON_PLATFORM]["runtime"][0]["sha256"] = "0" * 64
        with mock.patch.object(DEPS, "read_lock", return_value=lock), \
                mock.patch.object(DEPS.subprocess, "run") as process:
            with self.assertRaisesRegex(ValueError, "disagrees"):
                DEPS.install_python(Path("python"), PACKAGE, Path("unused"))
        process.assert_not_called()

    def test_unhashed_and_duplicate_requirements_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "requirements.txt"
            valid = "package==1.0 --hash=sha256:" + "a" * 64 + "\n"
            for content in ("package==1.0\n", valid + valid, "", "--index-url https://example.test\n"):
                path.write_text(content)
                with self.subTest(content=content), self.assertRaises(ValueError):
                    DEPS.requirements(path)

    def test_installer_is_offline_and_bootstrap_precedes_runtime(self):
        with mock.patch.object(DEPS, "fetch_python", return_value=Path("distributions")) as fetch, \
                mock.patch.object(DEPS.subprocess, "run") as process:
            DEPS.install_python(Path("python"), PACKAGE, Path("cache"),
                                env={"PIP_INDEX_URL": "https://untrusted.test", "PYTHONPATH": "untrusted"})
        fetch.assert_called_once_with(PACKAGE, Path("cache"), DEPS.PYTHON_PLATFORM, offline=True)
        for call, filename in zip(process.call_args_list[:2], ("python-bootstrap.txt", "python.txt")):
            command = call.args[0]
            for flag in ("-I", "--isolated", "--no-index", "--no-deps", "--no-cache-dir", "--no-build-isolation", "--require-hashes"):
                self.assertIn(flag, command)
            self.assertEqual(command[-1], str(PACKAGE / "locks" / filename))
            self.assertNotIn("PYTHONPATH", call.kwargs["env"])
        self.assertEqual(process.call_args_list[-1].args[0][-1], "check")
        self.assertIn("-I", process.call_args_list[-1].args[0])

    def test_contract_dependency_uses_portable_hashed_wheel(self):
        with tempfile.TemporaryDirectory() as temporary:
            saved = []
            def capture(python, requirement_file, directory):
                saved.extend(DEPS.requirements(requirement_file))
            with mock.patch.object(DEPS, "fetch") as fetch, \
                    mock.patch.object(DEPS, "install_requirements", side_effect=capture):
                DEPS.install_contract_dependency("python", PACKAGE, Path(temporary))
            self.assertEqual(saved[0]["name"], "ruamel.yaml")
            self.assertEqual(saved[0]["sha256"], fetch.call_args.args[0]["sha256"])

    def test_opam_initialization_uses_only_an_empty_local_repository(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch.object(DEPS.subprocess, "run") as process:
                DEPS.initialize_opam(root, root, {})
            command = process.call_args.args[0]
            self.assertIn("--no-opamrc", command)
            self.assertIn("--kind=local", command)
            self.assertEqual((root / "opam-repository/repo").read_text(), 'opam-version: "2.0"\n')
            self.assertNotIn("https://opam.ocaml.org", command)


class PythonLicenseEvidenceTest(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("dependency_inventory", PACKAGE / "licensing/inventory.py")
        self.inventory = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.inventory)

    def test_partial_collection_preserves_other_groups_and_replaces_python_group(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "evidence.json"
            engine = {"group": "engine", "provenance": {"revision": "retained"}, "evidence": []}
            path.write_text(json.dumps({"schema_version": 1, "components": {
                "engine/opengrep": engine, "python/old": {"group": "python", "evidence": []}}}))
            new = {"python/pip": {"group": "python", "provenance": {"linkage": "build-only"}, "evidence": []}}
            with mock.patch.object(self.inventory, "EVIDENCE_LOCK", path), \
                    mock.patch.object(self.inventory.sources, "enumerate_components", return_value={"python_packages": []}), \
                    mock.patch.object(self.inventory, "python_evidence", return_value=new), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(self.inventory.collect_python(SimpleNamespace(cache=None)), 0)
            result = json.loads(path.read_text())["components"]
            self.assertEqual(result, {"engine/opengrep": engine, **new})

    def test_license_extraction_never_sees_wrong_distribution_bytes(self):
        pin = dict(distribution(), name="package", version="1.0", linkage="build-only")
        with mock.patch.object(self.inventory.fetch, "download", return_value=b"unreviewed"), \
                mock.patch.object(self.inventory.fetch, "licences_from_archive") as extraction:
            with self.assertRaisesRegex(ValueError, "differs from the build pin"):
                self.inventory.python_evidence([pin], None)
        extraction.assert_not_called()

    def test_evidence_check_detects_distribution_drift_without_version_change(self):
        pin = dict(distribution(), name="package", version="1.0", linkage="build-only")
        provenance = {"url": pin["url"], "filename": pin["filename"], "version": pin["version"],
                      "pinned_sha256": pin["sha256"], "actual_sha256": pin["sha256"], "linkage": "build-only"}
        lock = {"components": {"python/package": {"provenance": provenance, "evidence": []}}}
        with mock.patch.object(self.inventory, "load", return_value=lock), \
                mock.patch.object(self.inventory.sources, "enumerate_components", return_value={"ocaml": [], "python_packages": [pin]}), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.inventory.check(None), 0)
            provenance["pinned_sha256"] = "0" * 64
            self.assertEqual(self.inventory.check(None), 1)


if __name__ == "__main__":
    unittest.main()
