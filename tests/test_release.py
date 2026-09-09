import hashlib
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine/tests"))
import test_artifact as fixtures

SPEC = importlib.util.spec_from_file_location("release", ROOT / "scripts/release.py")
RELEASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RELEASE)


class ReleaseTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ArtifactTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.package = self.fixture.package
        self.licensing = self.package / "licensing"
        self.licensing.mkdir()
        self.identity = {"version": "1.29.0+paintedwolf.26", "revision": self.fixture.lock["revision"],
                         "interfaces_revision": self.fixture.lock["interfaces_revision"]}
        (self.licensing / "inventory.json").write_text(json.dumps({"artifact": self.identity}))
        self.notices = b"# Third-party notices \xe2\x80\x94 opengrep 1.29.0+paintedwolf.26\n\nFixture notices.\n"
        (self.licensing / "NOTICES-opengrep.md").write_bytes(self.notices)
        self.set_retained_source({"artifact_version": self.identity["version"]})
        signing = RELEASE.ARTIFACT.signing_module()
        for patch in (mock.patch.object(RELEASE.ARTIFACT, "native_target", return_value=("darwin", "arm64")),
                      mock.patch.object(signing, "compile_inspector", return_value=Path("inspector")),
                      mock.patch.object(signing, "inspect_image", return_value=self.fixture.provenance["signing"]["outer"])):
            patch.start()
            self.addCleanup(patch.stop)

    def set_retained_source(self, record):
        name = "locks/corresponding-source.json"
        retained = self.package / name
        retained.parent.mkdir(exist_ok=True)
        retained.write_text(json.dumps(record))
        self.fixture.lock["files"][name] = RELEASE.ARTIFACT.digest(retained)
        lock_bytes = json.dumps(self.fixture.lock).encode()
        for directory in (self.package, self.fixture.seed):
            (directory / "source-lock.json").write_bytes(lock_bytes)
        self.fixture.archive_entries["inputs/source-lock.json"] = lock_bytes
        self.fixture.archive_entries["inputs/" + name] = retained.read_bytes()
        self.fixture.write_archive()
        self.fixture.provenance["source_lock_sha256"] = hashlib.sha256(lock_bytes).hexdigest()
        self.fixture.refresh_provenance()
        self.directory = self.fixture.resolve(seed=self.fixture.seed, no_build=True)

    def pack(self, output="release", **kwargs):
        return RELEASE.pack(self.directory, self.fixture.root / output, "v1.29.0+paintedwolf.26",
                            kwargs.get("channel", "prerelease"), self.package)

    def test_package_is_deterministic_flat_and_pinned(self):
        first, second = self.pack("first"), self.pack("second")
        self.assertEqual(first, second)
        metadata = first["opengrep"]
        entry = metadata["artifacts"][0]
        archive = self.fixture.root / "first" / entry["url"].rsplit("/", 1)[1]
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), entry["sha256"])
        self.assertEqual(archive.stat().st_size, entry["bytes"])
        self.assertEqual(archive.read_bytes(), (self.fixture.root / "second" / archive.name).read_bytes())
        with tarfile.open(archive) as packed:
            self.assertEqual(packed.getnames(), sorted(RELEASE.PAYLOADS))
            for member in packed:
                self.assertTrue(member.isfile())
                self.assertEqual((member.uid, member.gid, member.mtime), (0, 0, 0))
                self.assertEqual(member.mode, 0o755 if member.name == "opengrep" else 0o644)
            self.assertEqual(packed.extractfile("NOTICES-opengrep.md").read(), self.notices)
        self.assertEqual(metadata["source_lock_sha256"], RELEASE.ARTIFACT.digest(self.package / "source-lock.json"))
        with tarfile.open(self.directory / "opengrep-source.tar.gz") as source:
            expected = hashlib.sha256(source.extractfile("SOURCE-MANIFEST.json").read()).hexdigest()
        self.assertEqual(metadata["source_manifest_sha256"], expected)

    def test_changed_executable_cannot_be_packaged(self):
        (self.directory / "opengrep").write_bytes(b"different executable")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            self.pack()
        self.assertFalse((self.fixture.root / "release").exists())

    def test_license_must_match_authenticated_source_archive(self):
        (self.directory / "LICENSE").write_bytes(b"wrong license")
        with self.assertRaisesRegex(ValueError, "[Ll]icense differs"):
            self.pack()

    def test_adhoc_cannot_be_labeled_stable(self):
        with self.assertRaisesRegex(ValueError, "Stable releases require Developer ID"):
            self.pack(channel="stable")

    def test_native_signature_must_match_provenance(self):
        with mock.patch.object(RELEASE.ARTIFACT.signing_module(), "inspect_image", return_value={}), \
             self.assertRaisesRegex(ValueError, "signature differs"):
            self.pack()

    def test_notices_require_matching_versioned_inventory(self):
        self.identity["revision"] = "wrong revision"
        (self.licensing / "inventory.json").write_text(json.dumps({"artifact": self.identity}))
        with self.assertRaisesRegex(ValueError, "Notices inventory identity differs"):
            self.pack()

    def test_preflight_rejects_stale_release_payload_identity(self):
        inventory = self.licensing / "inventory.json"
        for key in ("version", "revision", "interfaces_revision"):
            with self.subTest(key=key):
                inventory.write_text(json.dumps({"artifact": dict(self.identity, **{key: "stale"})}))
                with self.assertRaisesRegex(ValueError, "Notices inventory identity differs: " + key):
                    RELEASE.release_input_bytes(self.package, self.fixture.lock)
        inventory.write_text(json.dumps({"artifact": self.identity}))
        (self.licensing / "NOTICES-opengrep.md").write_bytes(self.notices.replace(b"paintedwolf.26", b"paintedwolf.25"))
        with self.assertRaisesRegex(ValueError, "Notices version differs"):
            RELEASE.release_input_bytes(self.package, self.fixture.lock)

    def test_preflight_and_pack_reject_wrong_or_missing_retained_version(self):
        for record in ({"artifact_version": "1.29.0+paintedwolf.25"},
                       {"artifact_version": 26}, {}):
            with self.subTest(record=record):
                self.set_retained_source(record)
                with self.assertRaisesRegex(ValueError, "Retained source version differs"):
                    RELEASE.release_input_bytes(self.package, self.fixture.lock)
                with self.assertRaisesRegex(ValueError, "Retained source version differs"):
                    self.pack()
                self.assertFalse((self.fixture.root / "release").exists())

    def test_check_inputs_cli_needs_no_artifact_and_does_not_pack(self):
        output = io.StringIO()
        with mock.patch.object(RELEASE, "PACKAGE", self.package), \
                mock.patch.object(sys, "argv", ["release.py", "--check-inputs"]), \
                mock.patch.object(RELEASE, "pack") as pack, contextlib.redirect_stdout(output):
            RELEASE.main()
        pack.assert_not_called()
        self.assertIn("release metadata verified", output.getvalue())

    def test_cli_rejects_ambiguous_or_incomplete_modes(self):
        cases = ([], ["--artifact", "artifact"],
                 ["--check-inputs", "--artifact", "artifact"],
                 ["--check-inputs", "--output", "output"],
                 ["--check-inputs", "--tag", "vtest"],
                 ["--check-inputs", "--channel", "stable"])
        for arguments in cases:
            with self.subTest(arguments=arguments), \
                    mock.patch.object(sys, "argv", ["release.py", *arguments]), \
                    contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                RELEASE.main()
            self.assertEqual(error.exception.code, 2)

    def test_output_and_release_tag_are_not_overwritten(self):
        self.pack()
        with self.assertRaisesRegex(ValueError, "must not already exist"):
            self.pack()
        with self.assertRaisesRegex(ValueError, "tag must match"):
            RELEASE.pack(self.directory, self.fixture.root / "other", "vwrong", "prerelease", self.package)

    def test_consumer_size_limits_reject_before_publication(self):
        for limit, message in (("MAX_MEMBER_BYTES", "member exceeds"),
                               ("MAX_EXPANDED_BYTES", "expanded size limit"),
                               ("MAX_ARCHIVE_BYTES", "compressed size limit")):
            with self.subTest(limit=limit), mock.patch.object(RELEASE, limit, 1):
                with self.assertRaisesRegex(ValueError, message):
                    self.pack()
                self.assertFalse((self.fixture.root / "release").exists())

    def test_missing_payload_is_rejected(self):
        (self.directory / "runtime.json").unlink()
        with self.assertRaises(FileNotFoundError):
            self.pack()


if __name__ == "__main__":
    unittest.main()
