import copy
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import release_provenance as PROVENANCE
import promote as PROMOTE

SPEC = importlib.util.spec_from_file_location("release_signing_cli", SCRIPTS / "release_signing.py")
SIGNING = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SIGNING)


class ProvenanceTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.handoff = self.root / "handoff.tar.gz"
        self.handoff.write_bytes(b"compiled unsigned handoff")
        self.lock = {"upstream_version": "1.30.0", "patch_version": 33, "revision": "b" * 40}
        self.sha = "a" * 40
        self.environment = {"GITHUB_SERVER_URL": "https://github.com", "GITHUB_REPOSITORY": PROVENANCE.REPOSITORY,
            "GITHUB_REPOSITORY_ID": PROVENANCE.REPOSITORY_ID, "GITHUB_REPOSITORY_OWNER_ID": PROVENANCE.OWNER_ID,
            "GITHUB_SHA": self.sha, "GITHUB_WORKFLOW_SHA": self.sha, "GITHUB_REF_TYPE": "tag",
            "GITHUB_REF_NAME": "v1.30.0+paintedwolf.33", "GITHUB_REF": "refs/tags/v1.30.0+paintedwolf.33",
            "GITHUB_WORKFLOW_REF": PROVENANCE.REPOSITORY + "/" + PROVENANCE.WORKFLOW + "@refs/tags/v1.30.0+paintedwolf.33",
            "GITHUB_EVENT_NAME": "workflow_dispatch", "RUNNER_ENVIRONMENT": "github-hosted",
            "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "2", "GITHUB_JOB": "compile",
            "ImageOS": "macos15", "ImageVersion": "20260908.1", "RUNNER_OS": "macOS", "RUNNER_ARCH": "ARM64"}
        self.identity = {**PROVENANCE.workflow_identity(self.environment, self.lock), "source_lock_sha256": "c" * 64}
        self.evidence = PROVENANCE.build_evidence(self.handoff, self.identity, self.environment, {"clang": "Apple clang 17"})

    def test_workflow_identity_binds_reviewed_source_and_host(self):
        for key, value in (("GITHUB_WORKFLOW_SHA", "b" * 40), ("GITHUB_REPOSITORY_ID", "999"),
                           ("GITHUB_REPOSITORY_OWNER_ID", "999"), ("GITHUB_REF_NAME", "vwrong"),
                           ("GITHUB_REF_TYPE", "branch"), ("RUNNER_ENVIRONMENT", "self-hosted"),
                           ("GITHUB_EVENT_NAME", "pull_request_target"), ("GITHUB_RUN_ATTEMPT", "0")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                PROVENANCE.workflow_identity(dict(self.environment, **{key: value}), self.lock)

    def test_tag_checkout_and_main_ancestry_are_required(self):
        (self.root / "engine").mkdir()
        (self.root / "engine/source-lock.json").write_text(json.dumps(self.lock))
        for outputs in (("b" * 40,), (self.sha, "b" * 40), (self.sha, self.sha, " M engine/build.py")):
            with self.subTest(outputs=outputs), mock.patch.object(PROVENANCE, "command", side_effect=outputs), \
                    mock.patch.object(PROVENANCE.subprocess, "run"), self.assertRaises(ValueError):
                PROVENANCE.checked_identity(self.root, self.environment)
        with mock.patch.object(PROVENANCE, "command", side_effect=(self.sha, self.sha)), \
                mock.patch.object(PROVENANCE.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "git")), \
                self.assertRaises(subprocess.CalledProcessError):
            PROVENANCE.checked_identity(self.root, self.environment)

    def test_existing_draft_blocks_reuse(self):
        with mock.patch.object(PROVENANCE, "command", return_value=json.dumps([[{"tag_name": self.environment["GITHUB_REF_NAME"], "draft": True}]])), \
                self.assertRaisesRegex(ValueError, "already has a release or draft"):
            PROVENANCE.require_unpublished(self.identity)

    def test_build_evidence_rejects_other_run_source_reuse_or_handoff(self):
        PROVENANCE.check_evidence(self.evidence, self.identity, self.handoff)
        changes = (("build", dict(self.identity, run_attempt="1")), ("job", "release"), ("reused_artifact", True),
                   ("runner", dict(self.evidence["runner"], RUNNER_ARCH="X64")))
        for key, value in changes:
            with self.subTest(key=key), self.assertRaises(ValueError):
                PROVENANCE.check_evidence(dict(self.evidence, **{key: value}), self.identity, self.handoff)
        self.handoff.write_bytes(b"replaced handoff")
        with self.assertRaisesRegex(ValueError, "handoff differs"):
            PROVENANCE.check_evidence(self.evidence, self.identity, self.handoff)

    def test_only_compile_job_with_image_and_tools_can_record_build(self):
        for environment in (dict(self.environment, GITHUB_JOB="release"), dict(self.environment, ImageVersion="")):
            with self.subTest(environment=environment), self.assertRaises(ValueError):
                PROVENANCE.build_evidence(self.handoff, self.identity, environment, {"clang": "17"})
        with self.assertRaises(ValueError):
            PROVENANCE.build_evidence(self.handoff, self.identity, self.environment, {})

    def attestation(self):
        uri = "https://github.com/" + self.identity["workflow_ref"]
        return {"verificationResult": {"signature": {"certificate": {
            "subjectAlternativeName": uri, "buildSignerURI": uri, "issuer": "https://token.actions.githubusercontent.com",
            "buildSignerDigest": self.sha, "sourceRepositoryDigest": self.sha, "sourceRepositoryRef": self.identity["ref"],
            "sourceRepositoryURI": "https://github.com/" + PROVENANCE.REPOSITORY,
            "sourceRepositoryIdentifier": PROVENANCE.REPOSITORY_ID, "sourceRepositoryOwnerIdentifier": PROVENANCE.OWNER_ID,
            "runnerEnvironment": "github-hosted", "buildTrigger": "workflow_dispatch",
            "runInvocationURI": "https://github.com/" + PROVENANCE.REPOSITORY + "/actions/runs/"
            + self.identity["run_id"] + "/attempts/" + self.identity["run_attempt"]}},
            "verifiedTimestamps": [{"type": "tlog"}],
            "statement": {"predicateType": "https://slsa.dev/provenance/v1",
                          "subject": [{"digest": {"sha256": PROVENANCE.digest(self.handoff)}}]}}}

    def test_verified_certificate_identity_cannot_be_replaced_by_predicate_claims(self):
        valid = self.attestation()
        PROVENANCE.check_attestation([valid], self.identity, self.handoff)
        for field in valid["verificationResult"]["signature"]["certificate"]:
            changed = copy.deepcopy(valid)
            changed["verificationResult"]["signature"]["certificate"][field] = "wrong"
            changed["verificationResult"]["statement"]["predicate"] = valid["verificationResult"]["signature"]["certificate"]
            with self.subTest(field=field), self.assertRaises(ValueError):
                PROVENANCE.check_attestation([changed], self.identity, self.handoff)

    def test_verified_subject_timestamp_and_predicate_type_are_required(self):
        for section, value in (("verifiedTimestamps", []), ("statement", {"predicateType": "wrong"})):
            changed = self.attestation()
            changed["verificationResult"][section] = value
            with self.subTest(section=section), self.assertRaises(ValueError):
                PROVENANCE.check_attestation([changed], self.identity, self.handoff)
        self.handoff.write_bytes(b"different artifact")
        with self.assertRaises(ValueError):
            PROVENANCE.check_attestation([self.attestation_from_original()], self.identity, self.handoff)

    def attestation_from_original(self):
        value = self.attestation()
        value["verificationResult"]["statement"]["subject"][0]["digest"]["sha256"] = self.evidence["handoff"]["sha256"]
        return value

    def test_verification_uses_crypto_before_parsing_claims(self):
        with mock.patch.object(PROVENANCE, "command", side_effect=subprocess.CalledProcessError(1, "gh")) as command, \
                mock.patch.object(PROVENANCE, "check_attestation") as parse, self.assertRaises(subprocess.CalledProcessError):
            PROVENANCE.verify_attestation(self.handoff, self.root / "bundle.json", self.identity)
        parse.assert_not_called()
        arguments = command.call_args.args[0]
        self.assertIn("--deny-self-hosted-runners", arguments)
        self.assertEqual(arguments[arguments.index("--source-digest") + 1], self.sha)

    def test_uploaded_assets_must_be_complete_and_byte_identical(self):
        release = {"draft": True, "tag_name": self.environment["GITHUB_REF_NAME"], "assets": [
            {"name": self.handoff.name, "size": self.handoff.stat().st_size,
             "digest": "sha256:" + PROVENANCE.digest(self.handoff), "state": "uploaded"}]}
        PROMOTE.validate_uploaded_assets(release, [self.handoff], self.identity)
        for field, value in (("digest", "sha256:" + "0" * 64), ("state", "starter"), ("size", 1)):
            changed = copy.deepcopy(release)
            changed["assets"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                PROMOTE.validate_uploaded_assets(changed, [self.handoff], self.identity)
        for changed in (dict(release, draft=False), dict(release, assets=[]),
                        dict(release, assets=release["assets"] * 2)):
            with self.assertRaises(ValueError):
                PROMOTE.validate_uploaded_assets(changed, [self.handoff], self.identity)

    def test_imported_certificate_is_not_its_own_authority(self):
        policy = json.loads(SIGNING.POLICY.read_text())
        actual = SIGNING.SIGNING.SigningProfile.parse(policy, platform="darwin")
        SIGNING.validate_profile(actual, policy)
        for key, value in (("team_id", "ABCDEFGHIJ"), ("certificate_sha256", "a" * 64)):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "committed Developer ID"):
                SIGNING.validate_profile(SIGNING.SIGNING.SigningProfile.parse(dict(policy, **{key: value}), platform="darwin"), policy)

    def release_directory(self):
        directory = self.root / "release"
        directory.mkdir()
        (self.root / "engine").mkdir()
        (self.root / "engine/source-lock.json").write_text(json.dumps(self.lock))
        archive = directory / ("opengrep-" + self.identity["version"] + "-darwin-arm64.tar.gz")
        archive.write_bytes(b"already qualified signed archive")
        metadata = {"opengrep": {"version": self.identity["version"], "source_lock_sha256": self.identity["source_lock_sha256"],
            "upstream_version": self.lock["upstream_version"], "revision": self.lock["patch_version"],
            "base_revision": self.lock["revision"], "origin": "downstream", "license": "LGPL-2.1", "artifacts": [{
                "goos": "darwin", "goarch": "arm64", "sha256": PROVENANCE.digest(archive), "bytes": archive.stat().st_size,
                "url": "https://github.com/" + PROVENANCE.REPOSITORY + "/releases/download/"
                + self.environment["GITHUB_REF_NAME"] + "/" + archive.name}]}}
        (directory / "release.json").write_text(json.dumps(metadata))
        (directory / "build-evidence.json").write_text(json.dumps(self.evidence))
        (directory / "provenance.sigstore.json").write_text("verified by cryptographic verifier")
        return directory

    def test_promotion_rejects_changed_and_extra_assets_before_upload(self):
        directory = self.release_directory()
        with mock.patch.object(PROVENANCE, "ROOT", self.root):
            self.assertEqual(len(PROMOTE.release_files(directory, self.identity)), 4)
            (directory / "unexpected.txt").write_text("extra payload")
            with self.assertRaisesRegex(ValueError, "exactly the archive"):
                PROMOTE.release_files(directory, self.identity)
            (directory / "unexpected.txt").unlink()
            next(directory.glob("*.tar.gz")).write_bytes(b"different archive")
            with self.assertRaisesRegex(ValueError, "archive differs"):
                PROMOTE.release_files(directory, self.identity)

    def test_complete_draft_uses_release_permissions_without_administration_access(self):
        directory = self.release_directory()
        release = {"tag_name": self.environment["GITHUB_REF_NAME"], "draft": True, "html_url": "https://github.com/draft",
                   "assets": [{"name": path.name, "size": path.stat().st_size,
                               "digest": "sha256:" + PROVENANCE.digest(path), "state": "uploaded"}
                              for path in directory.iterdir()]}
        subjects = {path.name: PROVENANCE.digest(path) for path in directory.iterdir()
                    if path.name != "provenance.sigstore.json"}
        attestation = self.attestation()
        attestation["verificationResult"]["statement"]["subject"] = [
            {"name": name, "digest": {"sha256": digest}} for name, digest in subjects.items()]
        state_path = self.root / "gh-state.json"
        state_path.write_text(json.dumps({"identity": self.identity, "directory": str(directory),
            "subjects": subjects, "attestation": attestation, "release": release, "calls": []}))
        executable = self.root / "gh"
        shutil.copyfile(Path(__file__).with_name("fixtures") / "release_gh.py", executable)
        executable.chmod(0o755)
        with mock.patch.object(PROVENANCE, "ROOT", self.root), \
                mock.patch.dict(os.environ, {"PATH": str(self.root) + os.pathsep + os.environ["PATH"],
                                             "RELEASE_GH_STATE": str(state_path)}):
            self.assertEqual(PROMOTE.draft(directory, self.identity), release["html_url"])
        state = json.loads(state_path.read_text())
        self.assertTrue(state["created"])
        self.assertEqual([arguments[:2] for arguments in state["calls"]], [
            ["attestation", "verify"], ["attestation", "verify"], ["attestation", "verify"],
            ["api", "--paginate"], ["release", "create"], ["api", "--paginate"]])

    def test_unverified_release_never_creates_draft(self):
        directory = self.release_directory()
        with mock.patch.object(PROVENANCE, "ROOT", self.root), \
                mock.patch.object(PROVENANCE, "verify_attestation", side_effect=ValueError("invalid attestation")), \
                mock.patch.object(PROMOTE.subprocess, "run") as upload, self.assertRaises(ValueError):
            PROMOTE.draft(directory, self.identity)
        upload.assert_not_called()

    def test_cli_rejects_missing_and_cross_operation_arguments_before_work(self):
        cases = (
            (PROVENANCE, ["identity", "--handoff", "handoff.tar.gz"]),
            (PROVENANCE, ["check-evidence", "--evidence", "evidence.json", "--build-directory", "build"]),
            (PROVENANCE, ["build-evidence", "--handoff", "handoff.tar.gz", "--build-directory", "build"]),
            (SIGNING, ["prepare", "--helper", "inspector", "--certificate", "certificate.der"]),
            (SIGNING, ["check", "--helper", "inspector", "--profile", "profile.json"]),
            (SIGNING, ["profile", "--helper", "inspector", "--certificate", "certificate.der"]),
        )
        for module, arguments in cases:
            with self.subTest(arguments=arguments), mock.patch.object(sys, "argv", ["release", *arguments]), \
                    mock.patch.object(PROVENANCE, "checked_identity") as identity, \
                    mock.patch.object(SIGNING.SIGNING, "compile_inspector") as compile_helper, \
                    contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                module.main()
            self.assertEqual(error.exception.code, 2)
            identity.assert_not_called()
            compile_helper.assert_not_called()

    def test_build_tool_versions_come_from_the_completed_switch_and_python(self):
        with mock.patch.object(PROVENANCE, "command", return_value="tool version") as command:
            result = PROVENANCE.build_tool_versions(self.root)
        self.assertEqual(set(result), {"driver_python", "clang", "xcode", "opam", "node", "npm", "macos", "git",
                                       "ocaml", "dune", "packaging_python", "nuitka"})
        switch_probes = [call for call in command.call_args_list if call.args[0][:2] == ["opam", "exec"]]
        self.assertEqual(len(switch_probes), 2)
        for call in switch_probes:
            self.assertEqual(call.args[1], self.root / "engine")
            self.assertEqual(call.args[2]["OPAMROOT"], str(self.root / "opam"))
        python_probes = [call.args[0] for call in command.call_args_list
                         if call.args[0][0] == str(self.root / "python/bin/python")]
        self.assertEqual(len(python_probes), 2)


if __name__ == "__main__":
    unittest.main()
