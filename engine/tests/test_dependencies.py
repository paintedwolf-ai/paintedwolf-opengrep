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
            with self.subTest(data=data), self.response(data) as network, mock.patch.object(DEPS.time, "sleep") as sleep:
                with self.assertRaises(RuntimeError):
                    DEPS.fetch(distribution(expected), self.root)
                self.assertEqual(list(self.root.iterdir()), [])
                self.assertEqual(network.return_value.open.call_count, 1)
                sleep.assert_not_called()

    def test_transient_http_errors_retry_and_close_failed_responses(self):
        data = b"reviewed distribution"
        for status in (408, 429, 500, 502, 503, 504):
            body = io.BytesIO(b"unavailable")
            error = DEPS.urllib.error.HTTPError(distribution()["url"], status, "unavailable", {}, body)
            with self.subTest(status=status), mock.patch.object(DEPS.urllib.request, "build_opener") as network, \
                    mock.patch.object(DEPS.time, "sleep") as sleep:
                network.return_value.open.side_effect = [error, io.BytesIO(data)]
                target = DEPS.fetch(distribution(data), self.root)
                self.assertEqual(target.read_bytes(), data)
                self.assertEqual(network.return_value.open.call_count, 2)
                self.assertTrue(body.closed)
                sleep.assert_called_once_with(1)
                self.assertEqual(list(self.root.iterdir()), [target])
                target.unlink()

    def test_partial_stream_retry_discards_previous_bytes(self):
        data = b"reviewed distribution"
        for error in (TimeoutError(), ConnectionResetError(), DEPS.http.client.IncompleteRead(b"partial", 10)):
            response = mock.MagicMock()
            response.__enter__.return_value = response
            response.read.side_effect = [b"partial", error]
            with self.subTest(error=type(error).__name__), \
                    mock.patch.object(DEPS.urllib.request, "build_opener") as network, \
                    mock.patch.object(DEPS.time, "sleep") as sleep:
                network.return_value.open.side_effect = [response, io.BytesIO(data)]
                target = DEPS.fetch(distribution(data), self.root)
                self.assertEqual(target.read_bytes(), data)
                response.__exit__.assert_called_once()
                sleep.assert_called_once_with(1)
                self.assertEqual(list(self.root.iterdir()), [target])
                target.unlink()

    def test_wrapped_transport_errors_retry_with_bounded_backoff(self):
        errors = (TimeoutError(), ConnectionResetError(),
                  DEPS.socket.gaierror(DEPS.socket.EAI_AGAIN, "temporary DNS failure"))
        for reason in errors:
            error = DEPS.urllib.error.URLError(reason)
            with self.subTest(reason=type(reason).__name__), \
                    mock.patch.object(DEPS.urllib.request, "build_opener") as network, \
                    mock.patch.object(DEPS.time, "sleep") as sleep:
                network.return_value.open.side_effect = error
                with self.assertRaises(DEPS.urllib.error.URLError) as raised:
                    DEPS.fetch(distribution(), self.root)
                self.assertIs(raised.exception, error)
                self.assertEqual(network.return_value.open.call_count, 3)
                self.assertEqual(sleep.call_args_list, [mock.call(1), mock.call(2)])
                self.assertEqual(list(self.root.iterdir()), [])

    def test_permanent_http_tls_and_untyped_errors_never_retry(self):
        certificate = DEPS.ssl.SSLCertVerificationError(1, "certificate rejected")
        errors = [DEPS.urllib.error.HTTPError(distribution()["url"], status, "rejected", {}, io.BytesIO())
                  for status in (400, 401, 403, 404, 501)]
        errors += [certificate, DEPS.urllib.error.URLError(certificate),
                   DEPS.urllib.error.URLError("timed out"), DEPS.ssl.SSLError(1, "TLS rejected"),
                   DEPS.socket.gaierror(DEPS.socket.EAI_NONAME, "unknown host"), PermissionError()]
        for error in errors:
            with self.subTest(error=repr(error)), mock.patch.object(DEPS.urllib.request, "build_opener") as network, \
                    mock.patch.object(DEPS.time, "sleep") as sleep:
                network.return_value.open.side_effect = error
                with self.assertRaises(type(error)) as raised:
                    DEPS.fetch(distribution(), self.root)
                self.assertIs(raised.exception, error)
                self.assertEqual(network.return_value.open.call_count, 1)
                sleep.assert_not_called()
                self.assertEqual(list(self.root.iterdir()), [])

    def test_partial_stream_failure_cleans_temporary_file_after_final_attempt(self):
        responses = []
        for _ in range(DEPS.DOWNLOAD_ATTEMPTS):
            response = mock.MagicMock()
            response.__enter__.return_value = response
            response.read.side_effect = [b"partial", ConnectionResetError()]
            responses.append(response)
        with mock.patch.object(DEPS.urllib.request, "build_opener") as network, \
                mock.patch.object(DEPS.time, "sleep") as sleep:
            network.return_value.open.side_effect = responses
            with self.assertRaises(ConnectionResetError):
                DEPS.fetch(distribution(), self.root)
            self.assertEqual(network.return_value.open.call_count, DEPS.DOWNLOAD_ATTEMPTS)
            self.assertEqual(sleep.call_args_list, [mock.call(1), mock.call(2)])
            self.assertEqual(list(self.root.iterdir()), [])
            for response in responses:
                response.__exit__.assert_called_once()

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


class RetainedSourceMetadataTest(unittest.TestCase):
    def test_archive_commit_metadata_does_not_select_git_transport(self):
        spec = importlib.util.spec_from_file_location("retained_inventory", PACKAGE / "licensing/inventory.py")
        inventory = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(inventory)
        component = {"id": "ocaml/example", "group": "ocaml", "license": "LGPL-3.0",
                     "obligations": ["source-offer"], "provenance": {
                         "url": "https://example.test/source.tar.gz", "revision": "a" * 40,
                         "pinned_sha256": "b" * 64}}
        document = {"artifact": {"version": "1.0.0"}, "components": [component]}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "locks").mkdir()
            with mock.patch.object(inventory, "HERE", root / "licensing"), \
                    mock.patch.object(inventory, "load", return_value=document), \
                    mock.patch.object(inventory.sources, "opam_export", return_value=({}, set())), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(inventory.retained_lock(None), 0)
            retained = json.loads((root / "locks/corresponding-source.json").read_text())["retained"][0]
        self.assertEqual(retained["url"], component["provenance"]["url"])
        self.assertEqual(retained["sha256"], "b" * 64)
        self.assertIsNone(retained["revision"])


class OpamSourcePinTest(unittest.TestCase):
    def validate(self, body, extra=""):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "switch.export"
            path.write_text('package "example" {\n  url {\n' + body + '\n  }\n' + extra + '}\n')
            DEPS.validate_opam_sources(path)

    def test_all_frozen_sources_have_archive_checksums(self):
        DEPS.validate_opam_locks(PACKAGE)

    def test_sha256_and_sha512_archives_are_accepted(self):
        for algorithm, length in (("sha256", 64), ("sha512", 128)):
            with self.subTest(algorithm=algorithm):
                self.validate('    src:\n      "https://example.test/source.tar.gz"\n'
                              f'    checksum: ["{algorithm}={"a" * length}"]')

    def test_missing_weak_and_malformed_checksums_are_rejected(self):
        for checksum in ("", '    checksum: "md5=' + "a" * 32 + '"',
                         '    checksum: "sha256=' + "a" * 63 + '"',
                         '    checksum: []'):
            with self.subTest(checksum=checksum), self.assertRaises(ValueError):
                self.validate('    src: "https://example.test/source.tar.gz"\n' + checksum)

    def test_git_and_local_sources_cannot_bypass_archive_verification(self):
        for url in ("git+https://example.test/source.git#" + "a" * 40, "file:///tmp/source"):
            with self.subTest(url=url), self.assertRaisesRegex(ValueError, "HTTP archive"):
                self.validate(f'    src: "{url}"\n    checksum: "sha256={"a" * 64}"')

    def test_extra_sources_require_their_own_checksum(self):
        with self.assertRaises(ValueError):
            self.validate('    src: "https://example.test/source.tar.gz"\n'
                          f'    checksum: "sha256={"a" * 64}"',
                          '  extra-source "patch.diff" {\n    src: "https://example.test/patch.diff"\n  }\n')

    def test_unrecognized_source_layout_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "section layout"):
            self.validate('    src: "https://example.test/source.tar.gz"\n'
                          f'    checksum: "sha256={"a" * 64}"',
                          '  extra-source "patch.diff" { src: "https://example.test/patch.diff" }\n')


if __name__ == "__main__":
    unittest.main()
