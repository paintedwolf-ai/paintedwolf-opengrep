#!/usr/bin/env python3
"""Emit the raw source identity used by the native artifact resolver."""
import hashlib
import importlib.util
import os
from pathlib import Path


def main():
    package = Path(os.environ["GITHUB_WORKSPACE"]) / "engine"
    source = hashlib.sha256((package / "source-lock.json").read_bytes()).hexdigest()
    resolver = hashlib.sha256((package / "artifact.py").read_bytes()).hexdigest()
    spec = importlib.util.spec_from_file_location("opengrep_cache_artifact", package / "artifact.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    profile_path = os.environ.get("OPENGREP_SIGNING_PROFILE")
    profile = module.signing_module().SigningProfile.parse(
        module.read_json(Path(profile_path)) if profile_path else None, platform="darwin")
    key = module.artifact_cache_key(source, ("darwin", "arm64"), profile)
    cache = Path(os.environ.get("OPENGREP_CACHE_DIR") or ".cache/artifacts")
    artifact = cache / key
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        output.write(f"artifact-directory={artifact}\n")
        output.write(f"cache-key=opengrep-maintained-{key}-{resolver}\n")


if __name__ == "__main__":
    main()
