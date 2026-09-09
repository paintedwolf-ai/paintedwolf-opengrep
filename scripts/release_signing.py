#!/usr/bin/env python3
"""Prepare trusted inspection code before credentials enter a signing runner."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

SPEC = importlib.util.spec_from_file_location("release_signing", Path(__file__).resolve().parents[1] / "engine/signing/signing.py")
SIGNING = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SIGNING
SPEC.loader.exec_module(SIGNING)
POLICY = Path(__file__).resolve().parents[1] / "engine/signing/release-profile.json"


def validate_profile(actual, policy):
    expected = SIGNING.SigningProfile.parse(policy, platform="darwin")
    if expected.mode != "developer-id" or actual != expected:
        raise ValueError("Imported certificate differs from the committed Developer ID release policy")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    for operation in ("prepare", "profile", "check"):
        command = commands.add_parser(operation)
        command.add_argument("--helper", required=True, type=Path)
        if operation == "profile":
            command.add_argument("--certificate", required=True, type=Path)
            command.add_argument("--profile", required=True, type=Path)
    args = parser.parse_args()
    if args.operation == "prepare":
        if args.helper.exists():
            parser.error("the inspection helper must not already exist")
        SIGNING.compile_inspector(args.helper)
    elif args.operation == "profile":
        profile = SIGNING.profile_from_certificate(args.helper, args.certificate)
        validate_profile(profile, json.loads(POLICY.read_text()))
        with args.profile.open("x") as output:
            output.write(json.dumps(profile.record(), sort_keys=True, indent=2) + "\n")
    else:
        profile = SIGNING.SigningProfile.parse(json.loads(Path(os.environ["OPENGREP_SIGNING_PROFILE"]).read_text()))
        validate_profile(profile, json.loads(POLICY.read_text()))
        subprocess.run(["/usr/bin/codesign", "--force", "--options", "runtime", "--timestamp", "--sign",
                        os.environ["OPENGREP_SIGN_IDENTITY"], "--keychain",
                        str(Path(os.environ["RUNNER_TEMP"]) / "opengrep-signing.keychain-db"), str(args.helper)], check=True)
        SIGNING.inspect_image(args.helper, args.helper, profile)


if __name__ == "__main__":
    main()
