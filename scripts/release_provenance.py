#!/usr/bin/env python3
"""Bind release handoffs to the reviewed hosted workflow execution."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent
REPOSITORY = "paintedwolf-ai/paintedwolf-opengrep"
REPOSITORY_ID = "1362758908"
OWNER_ID = "289211278"
WORKFLOW = ".github/workflows/native-release.yml"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    require(path.is_file() and not path.is_symlink(), "Expected a regular release input: " + str(path))
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def command(argv, root=ROOT, environment=None):
    return subprocess.check_output(argv, cwd=root, text=True, env=environment).strip()


def workflow_identity(environment, lock):
    version = f'{lock["upstream_version"]}+paintedwolf.{lock["patch_version"]}'
    tag = "v" + version
    sha = environment["GITHUB_SHA"]
    require(re.fullmatch(r"[0-9a-f]{40}", sha) is not None, "Invalid workflow source commit")
    expected = {"GITHUB_SERVER_URL": "https://github.com", "GITHUB_REPOSITORY": REPOSITORY,
                "GITHUB_REPOSITORY_ID": REPOSITORY_ID, "GITHUB_REPOSITORY_OWNER_ID": OWNER_ID,
                "GITHUB_REF_TYPE": "tag", "GITHUB_REF_NAME": tag, "GITHUB_REF": "refs/tags/" + tag,
                "GITHUB_WORKFLOW_REF": REPOSITORY + "/" + WORKFLOW + "@refs/tags/" + tag,
                "GITHUB_WORKFLOW_SHA": sha, "GITHUB_EVENT_NAME": "workflow_dispatch",
                "RUNNER_ENVIRONMENT": "github-hosted"}
    for key, value in expected.items():
        require(environment.get(key) == value, "Unexpected release context: " + key)
    for key in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"):
        require(re.fullmatch(r"[1-9][0-9]*", environment.get(key, "")) is not None,
                "Invalid release run identity: " + key)
    return {"repository": REPOSITORY, "repository_id": REPOSITORY_ID, "owner_id": OWNER_ID,
            "commit": sha, "ref": expected["GITHUB_REF"], "version": version,
            "workflow_ref": expected["GITHUB_WORKFLOW_REF"], "workflow_sha": sha,
            "run_id": environment["GITHUB_RUN_ID"], "run_attempt": environment["GITHUB_RUN_ATTEMPT"]}


def checked_identity(root=ROOT, environment=None):
    environment = os.environ if environment is None else environment
    lock_path = root / "engine/source-lock.json"
    identity = workflow_identity(environment, json.loads(lock_path.read_text()))
    require(command(["git", "rev-parse", "HEAD"], root) == identity["commit"], "Checkout differs from workflow source")
    require(command(["git", "rev-parse", identity["ref"] + "^{commit}"], root) == identity["commit"],
            "Release tag differs from workflow source")
    subprocess.run(["git", "merge-base", "--is-ancestor", identity["commit"], "refs/remotes/origin/main"],
                   cwd=root, check=True)
    require(not command(["git", "status", "--porcelain", "--untracked-files=no"], root),
            "Release checkout has modified tracked inputs")
    return {**identity, "source_lock_sha256": digest(lock_path)}


def require_unpublished(identity):
    pages = json.loads(command(["gh", "api", "--paginate", "--slurp",
                               "repos/" + REPOSITORY + "/releases?per_page=100"]))
    require(not any(release["tag_name"] == identity["ref"].removeprefix("refs/tags/")
                    for page in pages for release in page),
            "This version already has a release or draft; existing assets will not be replaced")


def build_evidence(handoff, identity, environment, tools):
    require(environment.get("GITHUB_JOB") == "compile", "Build evidence must originate in the compile job")
    for key in ("ImageOS", "ImageVersion", "RUNNER_OS", "RUNNER_ARCH"):
        require(bool(environment.get(key)), "Missing hosted image identity: " + key)
    require(tools and all(isinstance(value, str) and value.strip() for value in tools.values()),
            "Build tool versions are incomplete")
    return {"schema_version": 1, "build": identity, "job": "compile", "reused_artifact": False,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "runner": {key: environment[key] for key in ("ImageOS", "ImageVersion", "RUNNER_OS", "RUNNER_ARCH")},
            "tools": tools, "handoff": {"sha256": digest(handoff), "bytes": handoff.stat().st_size}}


def check_evidence(evidence, identity, handoff=None):
    require(type(evidence.get("schema_version")) is int and evidence["schema_version"] == 1
            and evidence.get("build") == identity,
            "Build evidence differs from this source and workflow execution")
    require(evidence.get("job") == "compile" and evidence.get("reused_artifact") is False,
            "Release requires a fresh native compile")
    require(evidence.get("runner", {}).get("RUNNER_OS") == "macOS"
            and evidence["runner"].get("RUNNER_ARCH") == "ARM64", "Build runner is not macOS arm64")
    tools = evidence.get("tools")
    require(all(isinstance(evidence["runner"].get(key), str) and evidence["runner"][key]
                for key in ("ImageOS", "ImageVersion"))
            and isinstance(tools, dict) and tools
            and all(isinstance(key, str) and key and isinstance(value, str) and value.strip()
                    for key, value in tools.items()), "Build environment evidence is incomplete")
    recorded = evidence.get("handoff", {})
    require(isinstance(recorded.get("sha256"), str)
            and re.fullmatch(r"[a-f0-9]{64}", recorded["sha256"]) is not None
            and type(recorded.get("bytes")) is int and recorded["bytes"] > 0,
            "Build handoff identity is incomplete")
    if handoff is not None:
        require(evidence.get("handoff") == {"sha256": digest(handoff), "bytes": handoff.stat().st_size},
                "Unsigned handoff differs from build evidence")


def check_attestation(results, identity, subject):
    uri = "https://github.com/" + identity["workflow_ref"]
    expected = {"subjectAlternativeName": uri, "buildSignerURI": uri,
                "issuer": "https://token.actions.githubusercontent.com",
                "buildSignerDigest": identity["commit"], "sourceRepositoryDigest": identity["commit"],
                "sourceRepositoryRef": identity["ref"], "sourceRepositoryURI": "https://github.com/" + REPOSITORY,
                "sourceRepositoryIdentifier": REPOSITORY_ID, "sourceRepositoryOwnerIdentifier": OWNER_ID,
                "runnerEnvironment": "github-hosted", "buildTrigger": "workflow_dispatch",
                "runInvocationURI": "https://github.com/" + REPOSITORY + "/actions/runs/"
                + identity["run_id"] + "/attempts/" + identity["run_attempt"]}
    for result in results:
        verified = result.get("verificationResult", {})
        certificate = verified.get("signature", {}).get("certificate", {})
        statement = verified.get("statement", {})
        if (all(certificate.get(key) == value for key, value in expected.items())
                and verified.get("verifiedTimestamps")
                and statement.get("predicateType") == "https://slsa.dev/provenance/v1"
                and any(item.get("digest", {}).get("sha256") == digest(subject)
                        for item in statement.get("subject", []))):
            return
    raise ValueError("No verified attestation matches the exact hosted release identity")


def verify_attestation(subject, bundle, identity):
    output = command(["gh", "attestation", "verify", str(subject), "--bundle", str(bundle),
                      "--repo", REPOSITORY, "--signer-workflow", REPOSITORY + "/" + WORKFLOW,
                      "--source-ref", identity["ref"], "--source-digest", identity["commit"],
                      "--signer-digest", identity["commit"], "--deny-self-hosted-runners", "--format", "json"])
    check_attestation(json.loads(output), identity, subject)


def build_tool_versions(build):
    tools = {name: command(argv) for name, argv in {
        "driver_python": ["python3", "--version"], "clang": ["clang", "--version"],
        "xcode": ["xcodebuild", "-version"], "opam": ["opam", "--version"],
        "node": ["node", "--version"], "npm": ["npm", "--version"],
        "macos": ["sw_vers"], "git": ["git", "--version"]}.items()}
    environment = dict(os.environ, OPAMROOT=str(build / "opam"))
    for name, arguments in (("ocaml", ["ocamlc", "-version"]), ("dune", ["dune", "--version"])):
        tools[name] = command(["opam", "exec", "--", *arguments], build / "engine", environment)
    python = str(build / "python/bin/python")
    tools["packaging_python"] = command([python, "--version"])
    tools["nuitka"] = command([python, "-c", "import importlib.metadata; print(importlib.metadata.version('Nuitka'))"])
    return tools


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    commands.add_parser("identity")
    commands.add_parser("preflight")
    build = commands.add_parser("build-evidence")
    build.add_argument("--handoff", required=True, type=Path)
    build.add_argument("--build-directory", required=True, type=Path)
    build.add_argument("--output", required=True, type=Path)
    check = commands.add_parser("check-evidence")
    check.add_argument("--evidence", required=True, type=Path)
    check.add_argument("--handoff", type=Path)
    args = parser.parse_args()
    identity = checked_identity()
    if args.operation in ("identity", "preflight"):
        if args.operation == "preflight":
            require_unpublished(identity)
        result = identity
    elif args.operation == "build-evidence":
        tools = build_tool_versions(args.build_directory.resolve(strict=True))
        result = build_evidence(args.handoff, identity, os.environ, tools)
        with args.output.open("x") as output:
            output.write(json.dumps(result, sort_keys=True, indent=2) + "\n")
        return
    else:
        check_evidence(json.loads(args.evidence.read_text()), identity, args.handoff)
        result = {"verified": True}
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
