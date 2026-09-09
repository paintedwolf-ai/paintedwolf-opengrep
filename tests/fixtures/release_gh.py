#!/usr/bin/env python3
"""Exercise draft promotion with release permissions and no administration access."""
import hashlib
import json
import os
from pathlib import Path
import sys


def main():
    state_path = Path(os.environ["RELEASE_GH_STATE"])
    state = json.loads(state_path.read_text())
    arguments = sys.argv[1:]
    state["calls"].append(arguments)
    identity = state["identity"]
    directory = Path(state["directory"])
    if arguments[:2] == ["attestation", "verify"]:
        subject = Path(arguments[2])
        expected = ["--bundle", str(directory / "provenance.sigstore.json"),
                    "--repo", identity["repository"], "--signer-workflow", identity["workflow_ref"].split("@")[0],
                    "--source-ref", identity["ref"], "--source-digest", identity["commit"],
                    "--signer-digest", identity["commit"], "--deny-self-hosted-runners", "--format", "json"]
        assert arguments[3:] == expected
        assert subject.name in state["subjects"]
        assert hashlib.sha256(subject.read_bytes()).hexdigest() == state["subjects"][subject.name]
        result = [state["attestation"]]
    elif arguments == ["api", "--paginate", "--slurp", "repos/" + identity["repository"] + "/releases?per_page=100"]:
        result = [[state["release"]]] if state.get("created") else [[]]
    elif arguments[:2] == ["release", "create"]:
        assert not state.get("created")
        assert arguments[2] == identity["ref"].removeprefix("refs/tags/")
        assert arguments[3:11] == ["--repo", identity["repository"], "--verify-tag", "--draft",
                                   "--target", identity["commit"], "--title", arguments[2]]
        assert arguments[11] == "--notes-file" and Path(arguments[12]).is_file()
        assert len(arguments[13:]) == 4
        assert {Path(path).name for path in arguments[13:]} == {asset["name"] for asset in state["release"]["assets"]}
        state["created"] = True
        result = state["release"]["html_url"]
    else:
        state_path.write_text(json.dumps(state))
        sys.exit("Resource not accessible by integration: " + " ".join(arguments))
    state_path.write_text(json.dumps(state))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
