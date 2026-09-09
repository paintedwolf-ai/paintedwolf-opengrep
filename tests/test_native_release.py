import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(specification)
    sys.modules[name] = value
    specification.loader.exec_module(value)
    return value


NATIVE = load("native_release_test", ROOT / "engine/build_support/native_release.py")
SIGNING_CLI = load("release_signing_test", ROOT / "scripts/release_signing.py")


class NativeSigningBoundaryTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.package = self.root / "package"
        self.package.mkdir()
        (self.package / "source-lock.json").write_text('{"upstream_version":"1.30.0","patch_version":33}')
        self.payload = self.root / "payload"
        artifact = self.payload / "artifact"
        artifact.mkdir(parents=True)
        for name in ("opengrep", "provenance.json", "contracts.jsonl", "opengrep-source.tar.gz",
                     "platform-checks.json", "runtime.json", "LICENSE"):
            (artifact / name).write_bytes(b"fixture " + name.encode())
        shutil.copyfile(self.package / "source-lock.json", artifact / "source-lock.json")
        self.images = ("opengrep.bin", "semgrep/bin/opengrep-core", "library.dylib")
        for name in self.images:
            path = self.payload / "cli/entrypoint.dist" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"\xcf\xfa\xed\xfe" + name.encode())
            path.chmod(0o755)
        (self.payload / "cli/entrypoint.dist/settings.json").write_text("not executable")
        self.profile = NATIVE.SIGNING.SigningProfile.parse(json.loads((ROOT / "engine/signing/release-profile.json").read_text()), platform="darwin")
        self.inspector = self.root / "trusted-inspector"
        self.inspector.write_text("prepared before credentials")
        self.output = self.root / "next.tar.gz"
        self.signed = []
        for patch in (mock.patch.object(NATIVE, "PACKAGE", self.package),
                      mock.patch.object(NATIVE.subprocess, "run", side_effect=self.fake_codesign),
                      mock.patch.object(NATIVE.subprocess, "Popen", side_effect=AssertionError("payload or compiler executed")),
                      mock.patch.object(NATIVE.subprocess, "check_output", side_effect=AssertionError("payload or compiler executed")),
                      mock.patch.object(NATIVE.SIGNING, "compile_inspector", side_effect=AssertionError("compiler ran with credentials")),
                      mock.patch.object(NATIVE.SIGNING.execution_support(), "run_test_process", side_effect=AssertionError("payload executed while signing")),
                      mock.patch.object(NATIVE.SIGNING, "inspect_image", side_effect=self.inspect)):
            patch.start()
            self.addCleanup(patch.stop)

    def inspect(self, helper, image, profile, capacity=None):
        self.assertEqual(helper, self.inspector)
        self.assertEqual(profile, self.profile)
        return {"sha256": NATIVE.HANDOFF.digest(image), "bytes": image.stat().st_size}

    def fake_codesign(self, arguments, **kwargs):
        self.assertEqual(arguments[0], "/usr/bin/codesign")
        self.assertEqual(arguments[arguments.index("--sign") + 1], "reviewed identity")
        self.assertEqual(arguments[arguments.index("--keychain") + 1], str(self.root / "isolated.keychain"))
        self.assertIn("--timestamp", arguments)
        self.assertEqual(arguments[arguments.index("--options") + 1], "runtime")
        self.assertTrue(kwargs["check"])
        image = Path(arguments[-1])
        self.signed.append(image)
        image.write_bytes(image.read_bytes() + b" signed")
        return SimpleNamespace(returncode=0)

    def archive(self, stage="compiled", source_hash=None):
        path = self.root / (stage + ".tar.gz")
        NATIVE.HANDOFF.write(self.payload, path, source_hash or NATIVE.lock_hash(), stage, "paintedwolf-" + "a" * 64)
        return path

    def sign(self, archive, outer=False):
        NATIVE.sign(archive, self.output, self.inspector, self.profile,
                    "reviewed identity", self.root / "isolated.keychain", outer=outer)

    def test_inner_stage_only_signs_distribution_images_without_execution(self):
        before = NATIVE.HANDOFF.inventory(self.payload)
        archive = self.archive()
        self.sign(archive)
        result = self.root / "result"
        manifest = NATIVE.HANDOFF.read(self.output, result, NATIVE.lock_hash(), "inner-signed")
        targets = {"cli/entrypoint.dist/" + name for name in self.images}
        self.assertEqual(len(self.signed), len(targets))
        self.assertEqual({name for name, facts in before.items() if facts != manifest["files"][name]}, targets)
        self.assertEqual(NATIVE.HANDOFF.inventory(self.payload), before)
        self.assertEqual(manifest["build_id"], "paintedwolf-" + "a" * 64)

    def test_outer_stage_inspects_inner_images_and_only_signs_launcher(self):
        before = NATIVE.HANDOFF.inventory(self.payload)
        with mock.patch.object(NATIVE.SIGNING, "inspect_image", wraps=self.inspect) as inspections:
            self.sign(self.archive("packaged"), outer=True)
        manifest = NATIVE.HANDOFF.read(self.output, self.root / "result", NATIVE.lock_hash(), "outer-signed")
        self.assertEqual(len(self.signed), 1)
        self.assertEqual(self.signed[0].name, "opengrep")
        self.assertEqual(len(inspections.call_args_list), len(self.images) + 1)
        self.assertEqual({name for name, facts in before.items() if facts != manifest["files"][name]}, {"artifact/opengrep"})

    def test_wrong_stage_or_source_rejects_before_codesign(self):
        for stage, source_hash in (("inner-signed", None), ("compiled", "b" * 64)):
            with self.subTest(stage=stage), self.assertRaisesRegex(ValueError, "stage or source lock"):
                self.sign(self.archive(stage, source_hash))
        self.assertEqual(self.signed, [])
        self.assertFalse(self.output.exists())

    def test_missing_required_payload_rejects_before_codesign(self):
        (self.payload / "artifact/LICENSE").unlink()
        with self.assertRaisesRegex(ValueError, "artifact membership"):
            self.sign(self.archive())
        self.assertEqual(self.signed, [])

    def test_embedded_lock_must_match_even_when_manifest_claims_correct_source(self):
        (self.payload / "artifact/source-lock.json").write_text("different source")
        with self.assertRaisesRegex(ValueError, "artifact source lock differs"):
            self.sign(self.archive())
        self.assertEqual(self.signed, [])

    def test_signer_cannot_change_nonsigning_files(self):
        def corrupt(arguments, **kwargs):
            result = self.fake_codesign(arguments, **kwargs)
            root = next(parent for parent in Path(arguments[-1]).parents if parent.name == "handoff")
            (root / "artifact/runtime.json").write_text("unexpected signer mutation")
            return result
        with mock.patch.object(NATIVE.subprocess, "run", side_effect=corrupt), \
                self.assertRaisesRegex(ValueError, "outside the native signing targets"):
            self.sign(self.archive())
        self.assertFalse(self.output.exists())

    def test_failed_signature_validation_does_not_emit_next_stage(self):
        with mock.patch.object(NATIVE.SIGNING, "inspect_image", side_effect=ValueError("signature mismatch")), \
                self.assertRaisesRegex(ValueError, "signature mismatch"):
            self.sign(self.archive())
        self.assertFalse(self.output.exists())

    def test_existing_handoff_is_never_overwritten(self):
        self.output.write_bytes(b"previous completed handoff")
        with self.assertRaisesRegex(ValueError, "output must be new"):
            self.sign(self.archive())
        self.assertEqual(self.output.read_bytes(), b"previous completed handoff")

    def test_developer_signing_requires_explicit_keychain_and_identity(self):
        for identity, keychain in ((None, self.root / "isolated.keychain"), ("reviewed identity", None)):
            with self.subTest(identity=identity, keychain=keychain), self.assertRaisesRegex(ValueError, "isolated keychain"):
                NATIVE.codesign(self.payload / "artifact/opengrep", self.profile, identity, keychain)
        self.assertEqual(self.signed, [])

    def test_extracted_distribution_preserves_data_modes_and_links(self):
        standalone = self.payload / "cli/entrypoint.dist"
        (standalone / "settings-link").symlink_to("settings.json")
        extracted = self.root / "extracted"
        shutil.copytree(standalone, extracted, symlinks=True)
        NATIVE.verify_distribution(standalone, extracted)

    def test_extracted_distribution_rejects_non_native_changes(self):
        standalone = self.payload / "cli/entrypoint.dist"
        (standalone / "settings-link").symlink_to("settings.json")
        changes = {
            "data": lambda root: (root / "settings.json").write_text("modified data"),
            "missing": lambda root: (root / "settings-link").unlink(),
            "extra": lambda root: (root / "unexpected.json").write_text("extra data"),
            "mode": lambda root: (root / "settings.json").chmod(0o755),
            "link": lambda root: ((root / "settings-link").unlink(),
                                  (root / "settings-link").symlink_to("opengrep.bin")),
        }
        for name, change in changes.items():
            with self.subTest(name=name):
                extracted = self.root / name
                shutil.copytree(standalone, extracted, symlinks=True)
                change(extracted)
                with self.assertRaisesRegex(ValueError, "Extracted payload differs"):
                    NATIVE.verify_distribution(standalone, extracted)

    def compiled_build(self):
        build = self.root / "build"
        (build / "inputs").mkdir(parents=True)
        shutil.copyfile(self.package / "source-lock.json", build / "inputs/source-lock.json")
        shutil.copytree(self.payload / "artifact", build / "artifact")
        (build / "artifact/LICENSE").unlink()
        distribution = build / "engine/cli/entrypoint.dist"
        shutil.copytree(self.payload / "cli/entrypoint.dist", distribution)
        records = [{"path": name, "sha256": NATIVE.HANDOFF.digest(distribution / name),
                    "bytes": (distribution / name).stat().st_size} for name in self.images]
        (build / "artifact/provenance.json").write_text(json.dumps({"signing": {"standalone": records}}))
        return build

    def test_export_admits_completed_build_and_preserves_native_bytes(self):
        build = self.compiled_build()
        validator = mock.Mock(return_value=b"license from authenticated source")
        with mock.patch.object(NATIVE, "artifact_module", return_value=SimpleNamespace(validate_artifact=validator)):
            NATIVE.export(build, self.output)
        validator.assert_called_once()
        self.assertFalse(validator.call_args.kwargs["require_license"])
        self.assertEqual(validator.call_args.kwargs["profile"].mode, "adhoc")
        result = self.root / "result"
        NATIVE.HANDOFF.read(self.output, result, NATIVE.lock_hash(), "compiled")
        self.assertEqual((result / "artifact/LICENSE").read_bytes(), b"license from authenticated source")
        for name in self.images:
            self.assertEqual((result / "cli/entrypoint.dist" / name).read_bytes(),
                             (self.payload / "cli/entrypoint.dist" / name).read_bytes())
        self.assertFalse((build / "artifact/LICENSE").exists())
        self.assertEqual(self.signed, [])

    def test_export_rejects_different_compiled_source_before_admission(self):
        build = self.compiled_build()
        (build / "inputs/source-lock.json").write_text("wrong compiled source")
        validator = mock.Mock()
        with mock.patch.object(NATIVE, "artifact_module", return_value=SimpleNamespace(validate_artifact=validator)), \
                self.assertRaisesRegex(ValueError, "Compiled inputs differ"):
            NATIVE.export(build, self.output)
        validator.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_prepare_python_cli_accepts_workflow_output_flag(self):
        output = self.root / "locked-python"
        with mock.patch.object(sys, "argv", ["native_release.py", "prepare-python", "--output", str(output)]), \
                mock.patch.object(NATIVE.sys, "platform", "darwin"), \
                mock.patch.object(NATIVE.os, "uname", return_value=SimpleNamespace(machine="arm64")), \
                mock.patch.object(NATIVE, "prepare_python") as prepare:
            NATIVE.main()
        prepare.assert_called_once_with(output.resolve())


class SigningCredentialHelperTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.helper = self.root / "inspector"
        self.profile = SIGNING_CLI.SIGNING.SigningProfile.parse(json.loads(SIGNING_CLI.POLICY.read_text()), platform="darwin")

    def cli(self, *arguments):
        with mock.patch.object(sys, "argv", ["release_signing.py", *arguments]):
            SIGNING_CLI.main()

    def test_prepare_compiles_only_before_profile_or_signing(self):
        with mock.patch.object(SIGNING_CLI.SIGNING, "compile_inspector") as compile_helper, \
                mock.patch.object(SIGNING_CLI.SIGNING, "profile_from_certificate") as select_profile, \
                mock.patch.object(SIGNING_CLI.subprocess, "run") as sign:
            self.cli("prepare", "--helper", str(self.helper))
        compile_helper.assert_called_once_with(self.helper)
        select_profile.assert_not_called()
        sign.assert_not_called()

    def test_profile_uses_prepared_inspector_and_rejects_unreviewed_certificate(self):
        certificate, output = self.root / "cert.der", self.root / "profile.json"
        wrong = SIGNING_CLI.SIGNING.SigningProfile.parse(dict(self.profile.record(), certificate_sha256="a" * 64), platform="darwin")
        with mock.patch.object(SIGNING_CLI.SIGNING, "compile_inspector", side_effect=AssertionError("compiler after import")), \
                mock.patch.object(SIGNING_CLI.SIGNING, "profile_from_certificate", return_value=wrong), \
                self.assertRaisesRegex(ValueError, "committed Developer ID"):
            self.cli("profile", "--helper", str(self.helper), "--certificate", str(certificate), "--profile", str(output))
        self.assertFalse(output.exists())
        with mock.patch.object(SIGNING_CLI.SIGNING, "compile_inspector", side_effect=AssertionError("compiler after import")), \
                mock.patch.object(SIGNING_CLI.SIGNING, "profile_from_certificate", return_value=self.profile):
            self.cli("profile", "--helper", str(self.helper), "--certificate", str(certificate), "--profile", str(output))
        self.assertEqual(json.loads(output.read_text()), self.profile.record())

    def test_check_signs_and_inspects_prepared_probe_without_compilation(self):
        profile_path = self.root / "profile.json"
        profile_path.write_text(json.dumps(self.profile.record()))
        environment = {"RUNNER_TEMP": str(self.root), "OPENGREP_SIGNING_PROFILE": str(profile_path),
                       "OPENGREP_SIGN_IDENTITY": "reviewed identity"}
        with mock.patch.dict(SIGNING_CLI.os.environ, environment), \
                mock.patch.object(SIGNING_CLI.SIGNING.sys, "platform", "darwin"), \
                mock.patch.object(SIGNING_CLI.SIGNING, "compile_inspector", side_effect=AssertionError("compiler after import")), \
                mock.patch.object(SIGNING_CLI.subprocess, "run") as sign, \
                mock.patch.object(SIGNING_CLI.SIGNING, "inspect_image") as inspect:
            self.cli("check", "--helper", str(self.helper))
        arguments = sign.call_args.args[0]
        self.assertEqual(arguments[-1], str(self.helper))
        self.assertIn("--timestamp", arguments)
        self.assertEqual(arguments[arguments.index("--options") + 1], "runtime")
        self.assertEqual(arguments[arguments.index("--keychain") + 1], str(self.root / "opengrep-signing.keychain-db"))
        inspect.assert_called_once_with(self.helper, self.helper, self.profile)

    def test_check_rejects_unreviewed_profile_before_using_private_key(self):
        profile_path = self.root / "profile.json"
        profile_path.write_text(json.dumps(dict(self.profile.record(), certificate_sha256="a" * 64)))
        with mock.patch.dict(SIGNING_CLI.os.environ, {"OPENGREP_SIGNING_PROFILE": str(profile_path)}), \
                mock.patch.object(SIGNING_CLI.SIGNING.sys, "platform", "darwin"), \
                mock.patch.object(SIGNING_CLI.subprocess, "run") as sign, \
                self.assertRaisesRegex(ValueError, "committed Developer ID"):
            self.cli("check", "--helper", str(self.helper))
        sign.assert_not_called()

    def test_check_rejects_non_macos_before_using_private_key(self):
        profile_path = self.root / "profile.json"
        profile_path.write_text(json.dumps(self.profile.record()))
        with mock.patch.dict(SIGNING_CLI.os.environ, {"OPENGREP_SIGNING_PROFILE": str(profile_path)}), \
                mock.patch.object(SIGNING_CLI.SIGNING.sys, "platform", "linux"), \
                mock.patch.object(SIGNING_CLI.subprocess, "run") as sign, \
                mock.patch.object(SIGNING_CLI.SIGNING, "inspect_image") as inspect, \
                self.assertRaisesRegex(SIGNING_CLI.SIGNING.SigningError, "requires macOS"):
            self.cli("check", "--helper", str(self.helper))
        sign.assert_not_called()
        inspect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
