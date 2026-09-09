"""Signing policy, inspected payload identity, and native read-only controls."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location("opengrep_signing", Path(__file__).with_name("signing.py"))
SIGNING = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SIGNING
SPEC.loader.exec_module(SIGNING)


def profile(developer=False):
    return SIGNING.SigningProfile.parse({"schema_version": 1, "mode": "developer-id" if developer else "adhoc",
                                        "team_id": "ABCDEFGHIJ" if developer else None,
                                        "certificate_sha256": "a" * 64 if developer else None}, platform="darwin")


def inspection(developer=False, raw=b"image"):
    return {"schema_version": 1, "ok": True, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
            "slices": [{"architecture": "arm64", "cpu_type": 16777228, "cpu_subtype": 0,
                        "identifier": "engine", "team_id": "ABCDEFGHIJ" if developer else None,
                        "certificate_sha256": "a" * 64 if developer else None,
                        "secure_timestamp": "2026-09-08T12:00:00Z" if developer else None,
                        "flags": 0x10000 if developer else 2, "entitlements": {}}]}


def signing_record(developer=False):
    value = profile(developer)
    result = inspection(developer)
    images = [{"path": "semgrep/bin/opengrep-core", **copy.deepcopy(result)}]
    return {"profile": value.record(), "profile_sha256": value.digest(), "outer": result,
            "standalone": images, "extracted": copy.deepcopy(images)}


class ProfileTests(unittest.TestCase):
    def test_default_is_explicit_canonical_adhoc(self):
        with mock.patch.object(SIGNING, "execution_support", side_effect=AssertionError("native dependency loaded")):
            self.assertEqual(SIGNING.SigningProfile.parse(None), profile())
        self.assertNotEqual(profile().digest(), profile(True).digest())
        self.assertEqual(profile(True).digest(), SIGNING.SigningProfile.parse(dict(reversed(list(profile(True).record().items()))), platform="darwin").digest())

    def test_malformed_profiles_fail(self):
        cases = [{}, {**profile().record(), "schema_version": True}, {**profile().record(), "mode": "auto"},
                 {**profile().record(), "team_id": "ABCDEFGHIJ"},
                 {**profile(True).record(), "certificate_sha256": None},
                 {**profile(True).record(), "certificate_sha256": "A" * 64},
                 {**profile(True).record(), "team_id": "ABCDEFGHIJ\n"},
                 {**profile().record(), "entitlements": {}}]
        for value in cases:
            with self.subTest(value=value), self.assertRaises(SIGNING.SigningError):
                SIGNING.SigningProfile.parse(value, platform="darwin")
        with self.assertRaises(SIGNING.SigningError):
            SIGNING.SigningProfile.parse(profile(True).record(), platform="linux")


class InspectionTests(unittest.TestCase):
    def test_both_valid_profiles(self):
        for developer in (False, True):
            record = signing_record(developer)
            SIGNING.validate_signing_record(record, profile(developer), record["outer"]["sha256"], record["outer"]["bytes"])

    def test_invalid_native_facts_fail(self):
        changes = {
            "wrong team": {"team_id": "OTHERTEAM1"}, "wrong leaf": {"certificate_sha256": "b" * 64},
            "no secure timestamp": {"secure_timestamp": None}, "invalid date": {"secure_timestamp": "2026-99-08T12:00:00Z"},
            "signer date is insufficient": {"secure_timestamp": "Signed Time: today"},
            "no runtime": {"flags": 0}, "adhoc inner": {"flags": 0x10002},
            "exception entitlement": {"entitlements": {"com.apple.security.cs.disable-library-validation": True}},
            "false entitlement remains forbidden": {"entitlements": {"com.apple.security.get-task-allow": False}},
            "missing identifier": {"identifier": ""}, "bool flags": {"flags": True},
            "unknown CPU": {"cpu_type": None}}
        for label, update in changes.items():
            with self.subTest(label=label), self.assertRaises(SIGNING.SigningError):
                value = inspection(True)
                value["slices"][0].update(update)
                SIGNING.validate_inspection(value, profile(True), value["sha256"], value["bytes"])

    def test_every_slice_is_checked(self):
        value = inspection(True)
        second = copy.deepcopy(value["slices"][0])
        second.update(architecture="x86_64", cpu_type=16777223, cpu_subtype=3)
        value["slices"].append(second)
        SIGNING.validate_inspection(value, profile(True), value["sha256"], value["bytes"])
        for change in ({"team_id": "OTHERTEAM1"}, {"flags": 2}, {"cpu_type": 16777228, "cpu_subtype": 0}):
            invalid = copy.deepcopy(value)
            invalid["slices"][1].update(change)
            with self.subTest(change=change), self.assertRaises(SIGNING.SigningError):
                SIGNING.validate_inspection(invalid, profile(True), value["sha256"], value["bytes"])

    def test_malformed_inspections_fail(self):
        cases = [{**inspection(), "ok": False}, {**inspection(), "slices": []},
                 {**inspection(), "schema_version": True}, {**inspection(), "sha256": "0" * 64},
                 {**inspection(), "bytes": True}, {**inspection(), "extra": 1}]
        for value in cases:
            with self.subTest(value=value), self.assertRaises(SIGNING.SigningError):
                SIGNING.validate_inspection(value, profile(), inspection()["sha256"], 5)
        with self.assertRaises(SIGNING.SigningError):
            SIGNING.validate_inspection(inspection(True), profile(), inspection()["sha256"], 5)

    def test_signing_record_rejects_inconsistent_payloads(self):
        changes = {
            "profile hash": lambda r: r.update(profile_sha256="b" * 64),
            "wrong profile": lambda r: r.update(profile=profile(True).record()),
            "null profile is not recorded policy": lambda r: r.update(profile=None),
            "missing images": lambda r: r.update(standalone=[]),
            "extra extracted image": lambda r: r["extracted"].append({"path": "extra.so", **inspection()}),
            "missing core": lambda r: r["standalone"][0].update(path="other"),
            "different packed bytes": lambda r: r["extracted"][0].update(sha256="b" * 64),
            "contradictory signature facts": lambda r: r["extracted"][0]["slices"][0].update(identifier="another"),
            "traversing path": lambda r: r["standalone"][0].update(path="../core"),
            "duplicate image": lambda r: r["standalone"].append(r["standalone"][0]),
        }
        for label, change in changes.items():
            with self.subTest(label=label), self.assertRaises(SIGNING.SigningError):
                value = signing_record()
                change(value)
                SIGNING.validate_signing_record(value, profile(), inspection()["sha256"], 5)


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.image = self.root / "core"
        self.image.write_bytes(bytes.fromhex("cffaedfe") + b"fixture")

    def test_header_inventory_and_internal_alias(self):
        (self.root / "script.dylib").write_text("not a Mach-O")
        (self.root / "alias").symlink_to("core")
        self.assertEqual(list(SIGNING.image_inventory(self.root)), ["core"])

    def test_bad_symlinks_fail(self):
        for target in ("/usr/bin/true", "missing", "alias"):
            link = self.root / "alias"
            link.symlink_to(target)
            with self.subTest(target=target), self.assertRaises(SIGNING.SigningError):
                SIGNING.image_inventory(self.root)
            link.unlink()

    def test_postqualification_change_fails(self):
        digest, size = SIGNING.image_digest(self.image)
        records = [{"path": "core", "sha256": digest, "bytes": size}]
        SIGNING.verify_inventory_unchanged(self.root, records)
        self.image.write_bytes(self.image.read_bytes() + b"changed")
        with self.assertRaises(SIGNING.SigningError):
            SIGNING.verify_inventory_unchanged(self.root, records)

    def test_failed_native_check_returns_no_record(self):
        failure = mock.Mock(timed_out=False, returncode=1, stdout=json.dumps({"schema_version": 1, "ok": False,
                            "error": {"code": "security_status", "stage": "validity", "osstatus": -67062}}))
        with mock.patch.object(SIGNING.sys, "platform", "darwin"), mock.patch.object(SIGNING, "run_test_process", return_value=failure):
            with self.assertRaisesRegex(SIGNING.SigningError, "security_status"):
                SIGNING.inspect_inventory("helper", self.root, profile(), required=["core"])


@unittest.skipUnless(sys.platform == "darwin", "Security.framework requires macOS")
class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.helper = SIGNING.compile_inspector(cls.root / "inspector")

    def test_native_unsigned_rejected(self):
        image = self.root / "unsigned"
        image.write_bytes(bytes.fromhex("cffaedfe") + b"\x00" * 28)
        with self.assertRaises(SIGNING.SigningError):
            SIGNING.inspect_image(self.helper, image, profile())

    @unittest.skipUnless(__import__("platform").machine() == "arm64", "Apple arm64 linker supplies an ad-hoc signature")
    def test_linker_signature_validity_and_tamper(self):
        value = SIGNING.inspect_image(self.helper, self.helper, profile())
        self.assertEqual(value["slices"][0]["architecture"], "arm64")
        target = self.root / "tampered"
        shutil.copyfile(self.helper, target)
        with target.open("r+b") as stream:
            stream.seek(4096)
            current = stream.read(1)
            stream.seek(4096)
            stream.write(bytes([current[0] ^ 1]))
        with self.assertRaises(SIGNING.SigningError):
            SIGNING.inspect_image(self.helper, target, profile())

    def test_adhoc_cannot_satisfy_developer_id_requirement(self):
        with self.assertRaisesRegex(SIGNING.SigningError, "validity"):
            SIGNING.inspect_image(self.helper, self.helper, profile(True))

    def test_non_macho_rejected(self):
        image = self.root / "script"
        image.write_text("#!/bin/sh\n# regular source text\nexit 0\n")
        with self.assertRaisesRegex(SIGNING.SigningError, "not_macho"):
            SIGNING.inspect_image(self.helper, image, profile())

    def test_certificate_profile_uses_exact_single_subject_ou(self):
        key = self.root / "fixture-key.pem"
        capacity = SIGNING.execution_support().TestCapacity.detect()
        result = SIGNING.run_test_process(["openssl", "genrsa", "-out", key, "2048"], timeout=capacity.deadline(60))
        self.assertEqual(result.returncode, 0, result.stderr)
        subjects = {"valid": "/CN=Local test/OU=ABCDEFGHIJ", "missing": "/CN=Local test",
                    "duplicate": "/CN=Local test/OU=ABCDEFGHIJ/OU=ABCDEFGHIJ",
                    "different": "/CN=Local test/OU=ABCDEFGHIJ/OU=OTHERTEAM1",
                    "malformed": "/CN=Local test/OU=not-a-team"}
        for name, subject in subjects.items():
            with self.subTest(name=name):
                certificate = self.root / (name + ".der")
                result = SIGNING.run_test_process(["openssl", "req", "-new", "-x509", "-key", key,
                                                  "-days", "1", "-subj", subject, "-outform", "DER", "-out", certificate],
                                                 timeout=capacity.deadline(60))
                self.assertEqual(result.returncode, 0, result.stderr)
                if name == "valid":
                    selected = SIGNING.profile_from_certificate(self.helper, certificate)
                    self.assertEqual(selected.team_id, "ABCDEFGHIJ")
                    self.assertEqual(selected.certificate_sha256, hashlib.sha256(certificate.read_bytes()).hexdigest())
                else:
                    with self.assertRaises(SIGNING.SigningError):
                        SIGNING.profile_from_certificate(self.helper, certificate)


if __name__ == "__main__":
    unittest.main()
