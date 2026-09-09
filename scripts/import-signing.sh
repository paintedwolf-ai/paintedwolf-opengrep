#!/usr/bin/env bash
set -euo pipefail
umask 077
test -n "$APPLE_CERTIFICATE"
test -n "$APPLE_SIGNING_IDENTITY"
KEYCHAIN="$RUNNER_TEMP/opengrep-signing.keychain-db"
KEYCHAIN_PASSWORD="$(openssl rand -hex 32)"
echo "::add-mask::$KEYCHAIN_PASSWORD"
printf '%s' "$APPLE_CERTIFICATE" | base64 --decode > "$RUNNER_TEMP/signer.p12"
security create-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN"
security set-keychain-settings -lut 7200 "$KEYCHAIN"
security unlock-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN"
security import "$RUNNER_TEMP/signer.p12" -k "$KEYCHAIN" -P "$APPLE_CERTIFICATE_PASSWORD" -T /usr/bin/codesign
security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k "$KEYCHAIN_PASSWORD" "$KEYCHAIN"
security list-keychains -d user -s "$KEYCHAIN" "$HOME/Library/Keychains/login.keychain-db"
security find-certificate -c "$APPLE_SIGNING_IDENTITY" -p "$KEYCHAIN" > "$RUNNER_TEMP/signer.pem"
openssl x509 -in "$RUNNER_TEMP/signer.pem" -outform DER -out "$RUNNER_TEMP/signer.der"
python3 scripts/release_signing.py profile --helper "$RUNNER_TEMP/signature-inspector" --certificate "$RUNNER_TEMP/signer.der" --profile "$RUNNER_TEMP/signer.json"
echo "OPENGREP_SIGNING_PROFILE=$RUNNER_TEMP/signer.json" >> "$GITHUB_ENV"
echo "OPENGREP_SIGN_IDENTITY=$APPLE_SIGNING_IDENTITY" >> "$GITHUB_ENV"
rm "$RUNNER_TEMP/signer.p12" "$RUNNER_TEMP/signer.pem"
