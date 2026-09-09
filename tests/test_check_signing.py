import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location(
    "check_signing", Path(__file__).resolve().parents[1] / "scripts/check-signing.py")
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


class SigningCheckTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.profile = Path(directory.name) / "profile.json"
        self.profile.write_text(json.dumps({"schema_version": 1, "mode": "developer-id",
                                           "team_id": "ABCDEFGHIJ", "certificate_sha256": "a" * 64}))
        self.identity = "Developer ID Application: Test (ABCDEFGHIJ)"
        self.keychain = Path(directory.name) / "test.keychain-db"

    def run_probe(self, result, inspection=None):
        with mock.patch.object(CHECK.SIGNING.sys, "platform", "darwin"), \
             mock.patch.object(CHECK.SIGNING, "compile_inspector", side_effect=lambda path, capacity: path), \
             mock.patch.object(CHECK.SIGNING, "run_test_process", return_value=result) as sign, \
             mock.patch.object(CHECK.SIGNING, "inspect_image", side_effect=inspection) as inspect:
            CHECK.check_signing(self.profile, self.identity, self.keychain)
            return sign, inspect

    def test_signs_with_selected_key_and_inspects_exact_same_executable(self):
        sign, inspect = self.run_probe(SimpleNamespace(timed_out=False, returncode=0))
        command = sign.call_args.args[0]
        self.assertEqual(command[:-1], ["codesign", "--force", "--options", "runtime", "--timestamp",
                                       "--sign", self.identity, "--keychain", str(self.keychain)])
        helper, image, profile, capacity = inspect.call_args.args
        self.assertEqual(str(image), command[-1])
        self.assertEqual(helper, image)
        self.assertEqual(profile.certificate_sha256, "a" * 64)
        self.assertEqual(profile.team_id, "ABCDEFGHIJ")
        self.assertFalse(image.parent.exists())

    def test_signing_failure_and_timeout_cannot_pass(self):
        for result in (SimpleNamespace(timed_out=False, returncode=1),
                       SimpleNamespace(timed_out=True, returncode=0)):
            with self.subTest(result=result), self.assertRaises(CHECK.SIGNING.SigningError):
                self.run_probe(result)

    def test_native_identity_rejection_propagates(self):
        with self.assertRaisesRegex(CHECK.SIGNING.SigningError, "wrong signer"):
            self.run_probe(SimpleNamespace(timed_out=False, returncode=0),
                           CHECK.SIGNING.SigningError("wrong signer"))

    def test_adhoc_profile_and_empty_identity_are_refused(self):
        self.profile.write_text(json.dumps({"schema_version": 1, "mode": "adhoc",
                                           "team_id": None, "certificate_sha256": None}))
        with self.assertRaisesRegex(ValueError, "Developer ID"):
            CHECK.check_signing(self.profile, self.identity, self.keychain)
        with self.assertRaisesRegex(ValueError, "identity"):
            CHECK.check_signing(self.profile, "", self.keychain)


if __name__ == "__main__":
    unittest.main()
