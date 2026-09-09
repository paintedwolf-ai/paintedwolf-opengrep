#!/usr/bin/env python3
"""Prove release credentials can sign and validate a small native executable."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile

SPEC = importlib.util.spec_from_file_location(
    "release_signing_probe", Path(__file__).resolve().parents[1] / "engine/signing/signing.py")
SIGNING = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SIGNING
SPEC.loader.exec_module(SIGNING)


def check_signing(profile_path, identity, keychain):
    if not identity:
        raise ValueError("A release signing identity is required")
    profile = SIGNING.SigningProfile.parse(json.loads(Path(profile_path).read_text()))
    if profile.mode != "developer-id":
        raise ValueError("The signing check requires a Developer ID profile")
    capacity = SIGNING.execution_support().TestCapacity.detect()
    with tempfile.TemporaryDirectory(prefix="opengrep-signing-check-") as directory:
        helper = SIGNING.compile_inspector(Path(directory) / "inspect-signatures", capacity)
        result = SIGNING.run_test_process(
            ["codesign", "--force", "--options", "runtime", "--timestamp", "--sign", identity,
             "--keychain", str(keychain), str(helper)], timeout=capacity.deadline(120))
        if result.timed_out or result.returncode != 0:
            raise SIGNING.SigningError("Developer ID signing failed or timed out")
        SIGNING.inspect_image(helper, helper, profile, capacity)


def main():
    check_signing(os.environ["OPENGREP_SIGNING_PROFILE"], os.environ["OPENGREP_SIGN_IDENTITY"],
                  Path(os.environ["RUNNER_TEMP"]) / "opengrep-signing.keychain-db")
    print("Developer ID private key, certificate identity, hardened runtime, and secure timestamp validated.")


if __name__ == "__main__":
    main()
