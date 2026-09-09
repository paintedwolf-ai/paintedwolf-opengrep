#!/usr/bin/env bash
set -euo pipefail
if [[ -f "$RUNNER_TEMP/opengrep-signing.keychain-db" ]]; then
  security delete-keychain "$RUNNER_TEMP/opengrep-signing.keychain-db"
fi
rm -f "$RUNNER_TEMP/signer.p12" "$RUNNER_TEMP/signer.pem"
