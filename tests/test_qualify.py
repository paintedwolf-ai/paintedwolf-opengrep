import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine/tests"))
import test_artifact as fixtures

SPEC = importlib.util.spec_from_file_location("qualify", ROOT / "scripts/qualify.py")
QUALIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(QUALIFY)


class QualificationTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ArtifactTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.build = self.fixture.root / "completed"
        self.build.mkdir()
        self.entries = {}
        for name, raw in self.fixture.archive_entries.items():
            path = self.build / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(raw, dict):
                path.symlink_to(raw["symlink"])
            else:
                path.write_bytes(raw)
            self.entries[name] = path
        cli = self.build / "engine/cli"
        (cli / "entrypoint.dist").mkdir()
        shutil.copy2(self.fixture.seed / "opengrep", cli / "opengrep")
        for source, target in (("platform-checks.json", "platform-checks.json"),
                               ("runtime.json", "runtime/runtime.json"),
                               ("opengrep-source.tar.gz", "opengrep-source.tar.gz")):
            path = self.build / target
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.fixture.seed / source, path)
        (self.build / "contracts.jsonl").write_bytes(b"original failed contracts\n")
        self.profile = self.fixture.root / "profile.json"
        self.profile.write_text(json.dumps(self.fixture.provenance["signing"]["profile"]))
        self.output = self.fixture.root / "qualified"
        original_module = QUALIFY.module
        def selected_module(name, path):
            if name == "qualify_source_archive":
                return SimpleNamespace(source_entries=lambda *args: self.entries)
            return original_module(name, path)
        original_mkdtemp = tempfile.mkdtemp
        patches = [mock.patch.object(QUALIFY, "module", side_effect=selected_module),
                   mock.patch.object(QUALIFY.ARTIFACT, "native_target", return_value=("darwin", "arm64")),
                   mock.patch.object(QUALIFY.tempfile, "mkdtemp", side_effect=lambda **kwargs: original_mkdtemp(prefix=kwargs["prefix"], dir=self.fixture.root))]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def inspect(self, scratch, package, cli, profile, env):
        shutil.copy2(self.fixture.seed / "platform-checks.json", cli / "platform-checks.json")
        signing = mock.Mock()
        signing.inspect_image.return_value = self.fixture.provenance["signing"]["outer"]
        return signing, scratch / "inspector", scratch / "extracted", self.fixture.provenance["signing"], "1.29.0+paintedwolf.26"

    def contracts(self, build, package, cli, artifact, scratch, env):
        self.assertNotIn("build", Path(env["TMPDIR"]).parts)
        self.assertEqual(Path(env["XDG_CACHE_HOME"]), scratch / "cache")
        shutil.copy2(self.fixture.seed / "contracts.jsonl", artifact / "contracts.jsonl")

    def qualify(self):
        with mock.patch.object(QUALIFY, "inspect_runtime", side_effect=self.inspect), \
             mock.patch.object(QUALIFY, "run_contracts", side_effect=self.contracts):
            return QUALIFY.qualify(self.build, self.output, self.profile, self.fixture.package)

    def test_full_requalification_preserves_original_bytes_and_uses_regular_admission(self):
        before = {name: (self.build / name).read_bytes() for name in
                  ("contracts.jsonl", "opengrep-source.tar.gz", "engine/cli/opengrep", "platform-checks.json")}
        self.qualify()
        for name, raw in before.items():
            self.assertEqual((self.build / name).read_bytes(), raw)
        self.assertEqual((self.output / "opengrep").read_bytes(), self.fixture.binary)
        self.assertEqual((self.output / "opengrep-source.tar.gz").read_bytes(), before["opengrep-source.tar.gz"])
        QUALIFY.ARTIFACT.validate_artifact(self.output, self.fixture.package, self.fixture.lock, ("darwin", "arm64"))

    def test_changed_source_is_refused_before_contracts(self):
        self.entries["engine/upstream.c"].write_bytes(b"changed source")
        with mock.patch.object(QUALIFY, "inspect_runtime", side_effect=self.inspect), \
             mock.patch.object(QUALIFY, "run_contracts") as replay, self.assertRaisesRegex(ValueError, "source file differs"):
            QUALIFY.qualify(self.build, self.output, self.profile, self.fixture.package)
        replay.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_changed_executable_cannot_reuse_original_platform_record(self):
        (self.build / "engine/cli/opengrep").write_bytes(b"changed executable")
        with self.assertRaisesRegex(ValueError, "executable|launcher|digest"):
            self.qualify()
        self.assertFalse(self.output.exists())

    def test_changed_frozen_input_is_refused(self):
        (self.build / "inputs/verify.py").write_text("changed verifier")
        with self.assertRaisesRegex(RuntimeError, "differs|mismatch"):
            self.qualify()
        self.assertFalse(self.output.exists())

    def test_failed_replay_does_not_publish_or_replace_original_report(self):
        def failure(*args):
            (args[3] / "contracts.jsonl").write_text('{"contracts": 1, "failed": 1}\n')
            raise ValueError("frozen replay failed")
        with mock.patch.object(QUALIFY, "inspect_runtime", side_effect=self.inspect), \
             mock.patch.object(QUALIFY, "run_contracts", side_effect=failure), self.assertRaisesRegex(ValueError, "replay failed"):
            QUALIFY.qualify(self.build, self.output, self.profile, self.fixture.package)
        self.assertFalse(self.output.exists())
        self.assertEqual((self.build / "contracts.jsonl").read_bytes(), b"original failed contracts\n")
        self.assertTrue(list(self.fixture.root.glob("pwog-qualify-*/artifact/contracts.jsonl")))

    def test_final_admission_rejects_incomplete_replay(self):
        def incomplete(*args):
            (args[3] / "contracts.jsonl").write_text('{"contracts": 0, "failed": 0}\n')
        with mock.patch.object(QUALIFY, "inspect_runtime", side_effect=self.inspect), \
             mock.patch.object(QUALIFY, "run_contracts", side_effect=incomplete), self.assertRaisesRegex(ValueError, "incomplete"):
            QUALIFY.qualify(self.build, self.output, self.profile, self.fixture.package)
        self.assertFalse(self.output.exists())

    def test_existing_output_and_output_inside_original_build_are_refused(self):
        self.output.mkdir()
        with self.assertRaisesRegex(ValueError, "must be new"):
            self.qualify()
        with self.assertRaisesRegex(ValueError, "outside"):
            QUALIFY.qualify(self.build, self.build / "artifact", self.profile, self.fixture.package)


class VerifierOwnershipTest(unittest.TestCase):
    def test_interrupt_stops_verifier_and_scanner_and_preserves_peer(self):
        execution = QUALIFY.module("qualification_test_execution", ROOT / "engine/build_support/test_execution.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package, artifact = root / "inputs", root / "artifact"
            artifact.mkdir()
            (package / "build_support").mkdir(parents=True)
            shutil.copy2(ROOT / "engine/build_support/test_execution.py", package / "build_support/test_execution.py")
            (root / "python/bin").mkdir(parents=True)
            (root / "python/bin/python").symlink_to(sys.executable)
            ready = root / "ready.json"
            scanner = ('import json,os,socket,time; s=socket.socket(); s.bind(("127.0.0.1",0)); s.listen(); '
                       'open(os.environ["QUALIFICATION_READY"],"w").write(json.dumps({"pid":os.getpid(),"port":s.getsockname()[1]})); time.sleep(300)')
            (package / "verify.py").write_text('import sys\nfrom build_support.test_execution import run_test_process,test_run_signals\n'
                'with test_run_signals():\n    run_test_process([sys.executable,"-c",' + repr(scanner) + '],timeout=300)\n')
            original_popen = subprocess.Popen
            state = []
            def launch(*args, **kwargs):
                process = original_popen(*args, **kwargs)
                original_wait = process.wait
                def interrupt_once(timeout=None):
                    if not state:
                        deadline = time.monotonic() + execution.TestCapacity.detect().deadline(30)
                        while not ready.exists() or not ready.read_text():
                            if time.monotonic() > deadline:
                                raise AssertionError("owned scanner did not become ready")
                            time.sleep(0.01)
                        state.append(json.loads(ready.read_text()))
                        raise KeyboardInterrupt
                    return original_wait(timeout=timeout)
                process.wait = interrupt_once
                return process
            env = dict(os.environ, QUALIFICATION_READY=str(ready))
            with socket.socket() as peer:
                peer.bind(("127.0.0.1", 0))
                peer.listen()
                with mock.patch.object(QUALIFY.subprocess, "Popen", side_effect=launch), self.assertRaises(KeyboardInterrupt):
                    QUALIFY.run_contracts(root, package, root, artifact, root, env)
                with socket.socket() as probe:
                    self.assertNotEqual(probe.connect_ex(("127.0.0.1", state[0]["port"])), 0)
                with socket.create_connection(peer.getsockname(), timeout=30):
                    pass


if __name__ == "__main__":
    unittest.main()
