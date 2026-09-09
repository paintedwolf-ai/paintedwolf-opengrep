"""Contention-aware deadlines and owned subprocesses for scanner verification."""
import argparse
from contextlib import contextmanager
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Optional


@dataclass(frozen=True)
class TestCapacity:
    cpus: int
    load_one: Optional[float]
    timeout_scale: int
    scale_source: str

    @classmethod
    def detect(cls):
        try:
            cpus = len(os.sched_getaffinity(0)) or 4
        except (AttributeError, OSError):
            cpus = os.cpu_count() or 4
        try:
            load = os.getloadavg()[0]
        except (AttributeError, OSError):
            load = None
        explicit = os.environ.get("PW_TEST_TIMEOUT_SCALE")
        if explicit:
            if explicit not in ("1", "2", "3", "4"):
                raise ValueError("PW_TEST_TIMEOUT_SCALE must be an integer from 1 through 4")
            scale = int(explicit)
        else:
            # Same policy as scripts/test-host-capacity.sh; pin the scale to replay.
            scale = max(1, min(4, int(load / cpus) + 1)) if load is not None else 1
        return cls(cpus, load, scale, "environment" if explicit else "host-load" if load is not None else "default")

    def deadline(self, seconds):
        if seconds <= 0:
            raise ValueError("test deadline must be positive")
        return seconds * self.timeout_scale

    def record(self):
        return asdict(self)


@dataclass
class TestProcessResult:
    command: list
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool
    wall_seconds: float
    timeout_seconds: float

    def record(self):
        return asdict(self)


@contextmanager
def test_run_signals():
    """Unwind owned processes when a POSIX test entrypoint is interrupted."""
    previous = {}

    def interrupted(number, _frame):
        raise SystemExit(128 + number)

    if os.name == "posix":
        for number in (signal.SIGTERM, signal.SIGHUP):
            previous[number] = signal.signal(number, interrupted)
    try:
        yield
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


def stop_test_process(process):
    """Terminate the process group or job created by run_test_process."""
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    else:
        # Closing the child's job handle kills every scanner descendant.
        process.kill()


def run_test_process(command, *, timeout, env=None, cwd=None):
    """Capture failures without losing the suite; terminate only our process tree."""
    if timeout <= 0:
        raise ValueError("test deadline must be positive")
    command = [str(part) for part in command]
    actual = command
    if os.name == "nt":
        actual = [sys.executable, str(Path(__file__).resolve()), "--owned-child", *command]
    started = time.monotonic()
    process = subprocess.Popen(actual, env=env, cwd=cwd, text=True, encoding="utf-8",
                               errors="replace", stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=os.name == "posix")

    stopped = False

    def stop():
        nonlocal stopped
        if stopped:
            return
        stop_test_process(process)
        stopped = True

    timed_out = False
    try:
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            stop()
            stdout, stderr = process.communicate()
    finally:
        stop()
        process.communicate()
    return TestProcessResult(command, process.returncode, stdout, stderr, timed_out,
                             time.monotonic() - started, timeout)


def windows_owned_child(command):
    """Join a kill-on-close job before any scanner process can be spawned."""
    import ctypes
    from ctypes import wintypes

    class BasicLimit(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64),
                    ("PerJobUserTimeLimit", ctypes.c_int64), ("LimitFlags", wintypes.DWORD),
                    ("MinimumWorkingSetSize", ctypes.c_size_t), ("MaximumWorkingSetSize", ctypes.c_size_t),
                    ("ActiveProcessLimit", wintypes.DWORD), ("Affinity", ctypes.c_size_t),
                    ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]

    class IOCounters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class ExtendedLimit(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", BasicLimit), ("IoInfo", IOCounters),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.GetCurrentProcess.argtypes = []
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    job = kernel.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())
    limits = ExtendedLimit()
    limits.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
        raise ctypes.WinError(ctypes.get_last_error())
    if not kernel.AssignProcessToJobObject(job, kernel.GetCurrentProcess()):
        raise ctypes.WinError(ctypes.get_last_error())
    # The OS closes this non-inheritable handle on exit, including forced exit.
    return subprocess.call(command)


def harness_identity(*paths):
    return {str(path): hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in paths}


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--owned-child" and os.name == "nt":
        raise SystemExit(windows_owned_child(sys.argv[2:]))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("a command is required")
    capacity = TestCapacity.detect()
    with test_run_signals():
        result = run_test_process(command, timeout=capacity.deadline(args.timeout))
    print(json.dumps({"capacity": capacity.record(), **result.record()}))
    raise SystemExit(124 if result.timed_out else result.returncode)
