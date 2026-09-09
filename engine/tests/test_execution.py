"""Test scheduling policy and timeout cleanup without depending on startup speed."""
import json
import os
from pathlib import Path
import socket
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_support.test_execution import TestCapacity, run_test_process, stop_test_process, test_run_signals


class TestCapacityPolicy(unittest.TestCase):
    def test_contention_extends_deadlines_with_a_bounded_scale(self):
        for cpus, load, expected in [(1, 0, 1), (8, 7.9, 1), (8, 8, 2), (8, 16, 3), (8, 200, 4)]:
            with self.subTest(cpus=cpus, load=load), patch.dict(os.environ, {}, clear=True), \
                    patch('os.sched_getaffinity', side_effect=AttributeError, create=True), \
                    patch('os.cpu_count', return_value=cpus), patch('os.getloadavg', return_value=(load, 0, 0), create=True):
                capacity = TestCapacity.detect()
                self.assertEqual(capacity.timeout_scale, expected)
                self.assertEqual(capacity.deadline(120), 120 * expected)

    def test_explicit_scale_is_replayable_under_different_load(self):
        with patch.dict(os.environ, PW_TEST_TIMEOUT_SCALE='3'), \
                patch('os.getloadavg', return_value=(999, 999, 999), create=True):
            self.assertEqual(TestCapacity.detect().timeout_scale, 3)
            self.assertEqual(TestCapacity.detect().scale_source, 'environment')

    def test_invalid_scales_are_rejected(self):
        for value in ('0', '5', '1.5', '-1', '01', 'bad'):
            with self.subTest(value=value), patch.dict(os.environ, PW_TEST_TIMEOUT_SCALE=value):
                with self.assertRaises(ValueError):
                    TestCapacity.detect()

    def test_missing_load_api_uses_base_deadline(self):
        with patch.dict(os.environ, {}, clear=True), patch('os.cpu_count', return_value=None), \
                patch('os.getloadavg', side_effect=OSError, create=True):
            capacity = TestCapacity.detect()
            self.assertEqual(capacity.deadline(120), 120)
            self.assertIsNone(capacity.load_one)
            self.assertEqual(capacity.scale_source, "default")

    def test_cpu_affinity_bounds_capacity_inside_a_restricted_runner(self):
        with patch.dict(os.environ, {}, clear=True), patch('os.cpu_count', return_value=64), \
                patch('os.sched_getaffinity', return_value={0, 1}, create=True), \
                patch('os.getloadavg', return_value=(5, 0, 0), create=True):
            capacity = TestCapacity.detect()
            self.assertEqual(capacity.cpus, 2)
            self.assertEqual(capacity.timeout_scale, 3)


WORKER = '''import json, os, socket, subprocess, sys
if len(sys.argv) > 1:
    child = subprocess.Popen([sys.executable, "-c", sys.argv[1]], stdout=subprocess.PIPE, text=True)
    print(child.stdout.readline(), end="", flush=True)
    child.wait()
else:
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen()
    print(json.dumps({"pid": os.getpid(), "port": server.getsockname()[1]}), flush=True)
    while True:
        connection, _ = server.accept()
        connection.close()
'''


class OwnedTestProcess(unittest.TestCase):
    def test_captures_exit_and_output(self):
        result = run_test_process([sys.executable, '-c', 'import sys; print("out"); print("err", file=sys.stderr); sys.exit(7)'],
                                  timeout=TestCapacity.detect().deadline(30))
        self.assertEqual((result.returncode, result.stdout, result.stderr), (7, 'out\n', 'err\n'))
        self.assertFalse(result.timed_out)

    def test_timeout_stops_descendant_and_preserves_peer(self):
        self.assert_owned_cleanup(interrupt=False)

    @unittest.skipUnless(os.name == 'posix', 'POSIX signal delivery')
    def test_interruption_stops_descendant_and_preserves_peer(self):
        previous = signal.getsignal(signal.SIGTERM)
        self.assert_owned_cleanup(interrupt=True)
        self.assertEqual(signal.getsignal(signal.SIGTERM), previous)

    def assert_owned_cleanup(self, interrupt):
        communicate = subprocess.Popen.communicate
        observed = []
        timeout = TestCapacity.detect().deadline(30)

        def expire_after_readiness(process, *args, **kwargs):
            if observed:
                return communicate(process, *args, **kwargs)
            # The watchdog bounds setup only. Timeout is injected after the real
            # descendant is listening, so scheduler delay cannot race setup.
            watchdog = threading.Timer(timeout, stop_test_process, args=(process,))
            watchdog.start()
            try:
                line = process.stdout.readline()
                observed.append(json.loads(line))
            finally:
                watchdog.cancel()
                watchdog.join()
            if interrupt:
                signal.raise_signal(signal.SIGTERM)
            raise subprocess.TimeoutExpired(process.args, kwargs['timeout'])

        with socket.socket() as peer:
            peer.bind(('127.0.0.1', 0))
            peer.listen()
            with test_run_signals(), patch.object(subprocess.Popen, 'communicate', expire_after_readiness):
                if interrupt:
                    with self.assertRaises(SystemExit) as stopped:
                        run_test_process([sys.executable, '-c', WORKER, WORKER], timeout=timeout)
                    self.assertEqual(stopped.exception.code, 128 + signal.SIGTERM)
                else:
                    result = run_test_process([sys.executable, '-c', WORKER, WORKER], timeout=timeout)
                    self.assertTrue(result.timed_out)
                    self.assertNotEqual(result.returncode, 0)
            deadline = time.monotonic() + timeout
            while True:
                with socket.socket() as probe:
                    probe.settimeout(timeout)
                    if probe.connect_ex(('127.0.0.1', observed[0]['port'])) != 0:
                        break
                self.assertLess(time.monotonic(), deadline, "owned descendant survived cancellation")
                time.sleep(0.01)
            with socket.create_connection(peer.getsockname(), timeout=timeout):
                pass


if __name__ == '__main__':
    unittest.main()
