#!/usr/bin/env bash
# Re-run the Developer ID signing qualification experiments for the maintained
# Opengrep Nuitka executable. Needs no signing identity. Writes only under a
# scratch directory; never modifies the repo or ~/.cache/opengrep.
#
#   ./qualify.sh [scratch-dir]
#
# Requires: macOS, Xcode command line tools, an extracted maintained payload in
# ~/.cache/opengrep/paintedwolf-* (run the staged opengrep once to create one).
set -uo pipefail

SCRATCH="${1:-${TMPDIR:-/tmp}/opengrep-signing-qualify}"
mkdir -p "${SCRATCH}"
PASS=0
FAIL=0

ok()   { printf '  PASS  %s\n' "$1"; PASS=$((PASS+1)); }
bad()  { printf '  FAIL  %s\n' "$1"; FAIL=$((FAIL+1)); }
head_() { printf '\n== %s ==\n' "$1"; }

[[ "$(uname -s)" == "Darwin" ]] || { echo "macOS only"; exit 1; }

head_ "Environment"
printf '  macOS      %s (%s)\n' "$(sw_vers -productVersion)" "$(sw_vers -buildVersion)"
printf '  arch       %s\n' "$(uname -m)"
IDENTITIES="$(security find-identity -v -p codesigning 2>&1 | tail -1)"
printf '  identities %s\n' "${IDENTITIES}"

head_ "Check 1 — stapler does not support bare Mach-O"
# Note: these tools exit non-zero on usage/verify failure, so capture first and
# match afterwards — piping straight into grep would trip `set -o pipefail`.
STAPLER_USAGE="$(xcrun stapler --help 2>&1 || true)"
if grep -q 'UDIF disk images, code-signed executable' <<<"${STAPLER_USAGE}"; then
  grep -A1 'Supported file formats' <<<"${STAPLER_USAGE}" | sed 's/^/      /'
  ok "stapler supports only bundles / DMGs / flat packages"
else
  bad "could not read stapler supported formats"
fi

head_ "Check 2 — extracted payload keeps its signatures and exec bits"
# ~/.cache/opengrep is a live shared cache: concurrent opengrep runs create and
# reap sibling directories, so a dir chosen by mtime can vanish mid-run. Snapshot
# one complete payload into scratch and run every later check against that copy.
PAYLOAD=""
for candidate in $(ls -dt "${HOME}"/.cache/opengrep/paintedwolf-* 2>/dev/null); do
  [[ -f "${candidate}/semgrep/bin/opengrep-core" && -f "${candidate}/opengrep.bin" ]] || continue
  rm -rf "${SCRATCH}/payload-src"
  if cp -R "${candidate}" "${SCRATCH}/payload-src" 2>/dev/null \
     && [[ -f "${SCRATCH}/payload-src/semgrep/bin/opengrep-core" ]]; then
    PAYLOAD="${SCRATCH}/payload-src"
    printf '  source:  %s\n' "${candidate}"
    break
  fi
done
if [[ -z "${PAYLOAD}" ]]; then
  bad "no complete maintained payload under ~/.cache/opengrep (run the staged opengrep once)"
else
  printf '  payload: %s (snapshot)\n' "${PAYLOAD}"
  CORE="${PAYLOAD}/semgrep/bin/opengrep-core"
  if codesign -dvv "${CORE}" 2>&1 | grep -q 'CodeDirectory'; then
    ok "extracted opengrep-core carries an embedded signature"
  else
    bad "extracted opengrep-core has no signature"
  fi
  if [[ -x "${CORE}" ]]; then ok "extracted opengrep-core is executable"; else bad "opengrep-core not executable"; fi
  UNSIGNED=0
  while IFS= read -r f; do
    codesign -dvv "$f" >/dev/null 2>&1 || UNSIGNED=$((UNSIGNED+1))
  done < <(find "${PAYLOAD}" -type f -exec sh -c 'head -c4 "$1" | xxd -p | grep -qE "^(cffaedfe|cafebabe)$" && echo "$1"' _ {} \;)
  if (( UNSIGNED == 0 )); then ok "every payload Mach-O is signed (0 unsigned)"; else bad "${UNSIGNED} payload Mach-O(s) unsigned"; fi
fi

head_ "Check 3 — MAP_JIT under hardened runtime"
cat > "${SCRATCH}/jitprobe.c" <<'EOF'
#include <stdio.h>
#include <sys/mman.h>
int main(void){
  void *p = mmap(NULL,4096,PROT_READ|PROT_WRITE|PROT_EXEC,MAP_PRIVATE|MAP_ANON|MAP_JIT,-1,0);
  printf("%s\n", p==MAP_FAILED ? "FAILED" : "ok");
  return 0;
}
EOF
clang -o "${SCRATCH}/jitprobe" "${SCRATCH}/jitprobe.c" 2>/dev/null
cat > "${SCRATCH}/jit.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>com.apple.security.cs.allow-jit</key><true/></dict></plist>
EOF
A="$("${SCRATCH}/jitprobe")"
/usr/bin/codesign -s - --force --options=runtime "${SCRATCH}/jitprobe" 2>/dev/null
B="$("${SCRATCH}/jitprobe")"
/usr/bin/codesign -s - --force --options=runtime --entitlements "${SCRATCH}/jit.plist" "${SCRATCH}/jitprobe" 2>/dev/null
C="$("${SCRATCH}/jitprobe")"
printf '  no-runtime=%s  runtime=%s  runtime+allow-jit=%s\n' "$A" "$B" "$C"
if [[ "$A" == ok && "$B" == FAILED && "$C" == ok ]]; then
  ok "hardened runtime blocks MAP_JIT; allow-jit restores it"
else
  bad "unexpected MAP_JIT matrix"
fi

head_ "Check 4 — opengrep-core is correct under hardened runtime"
if [[ -n "${PAYLOAD}" ]]; then
  cp "${PAYLOAD}/semgrep/bin/opengrep-core" "${SCRATCH}/core-hr" && chmod +w "${SCRATCH}/core-hr"
  mkdir -p "${SCRATCH}/case"
  cat > "${SCRATCH}/case/target.py" <<'EOF'
SECRET = "AKIAIOSFODNN7EXAMPLE"
password = "hunter2hunter2hunter2"
EOF
  cat > "${SCRATCH}/case/rules.yaml" <<'EOF'
rules:
  - id: regex-jit-probe
    languages: [python]
    message: regex probe
    severity: WARNING
    patterns:
      - pattern-regex: '(AKIA[0-9A-Z]{16})|(?:pass|pwd)word\s*=\s*"(?:[A-Za-z0-9]{8,64})"'
EOF
  count() { ( cd "${SCRATCH}/case" && "$1" -rules rules.yaml -lang python -json target.py 2>/dev/null \
      | tail -1 | python3 -c 'import json,sys; d=json.loads(sys.stdin.read()); print(len(d["results"]), len(d["errors"]))' ); }
  BEFORE="$(count "${PAYLOAD}/semgrep/bin/opengrep-core")"
  /usr/bin/codesign -s - --force --options=runtime "${SCRATCH}/core-hr" 2>/dev/null
  AFTER="$(count "${SCRATCH}/core-hr")"
  printf '  adhoc="%s"  hardened="%s"  (results errors)\n' "${BEFORE}" "${AFTER}"
  if [[ -n "${BEFORE}" && "${BEFORE}" == "${AFTER}" ]]; then
    ok "hardened runtime changes neither results nor errors"
  else
    bad "hardened runtime changed scan behavior"
  fi
else
  bad "skipped — no payload"
fi

head_ "Check 5 — library validation trap (ad-hoc only)"
if [[ -n "${PAYLOAD}" ]]; then
  rm -rf "${SCRATCH}/payload-hr"
  cp -R "${PAYLOAD}" "${SCRATCH}/payload-hr" && chmod -R u+w "${SCRATCH}/payload-hr"
  find "${SCRATCH}/payload-hr" -type f -exec sh -c 'head -c4 "$1" | xxd -p | grep -qE "^(cffaedfe|cafebabe)$" && echo "$1"' _ {} \; \
    | awk '{print length($0)"\t"$0}' | sort -rn | cut -f2- \
    | while IFS= read -r f; do /usr/bin/codesign -s - --force --options=runtime "$f" 2>/dev/null; done
  OUT="$("${SCRATCH}/payload-hr/opengrep.bin" --version 2>&1)"
  if grep -q 'different Team IDs' <<<"${OUT}"; then
    ok "ad-hoc + hardened runtime fails library validation (expected; Developer ID would not)"
  else
    bad "expected a library-validation failure under ad-hoc, got: ${OUT}"
  fi
  cat > "${SCRATCH}/dlv.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>com.apple.security.cs.disable-library-validation</key><true/></dict></plist>
EOF
  /usr/bin/codesign -s - --force --options=runtime --entitlements "${SCRATCH}/dlv.plist" \
    "${SCRATCH}/payload-hr/opengrep.bin" 2>/dev/null
  RES="$( cd "${SCRATCH}/case" && "${SCRATCH}/payload-hr/opengrep.bin" scan --config rules.yaml --json target.py 2>/dev/null \
      | python3 -c 'import json,sys; d=json.load(sys.stdin); print(len(d["results"]), len(d["errors"]))' )"
  printf '  full hardened pipeline: results/errors = %s\n' "${RES}"
  if [[ "${RES}" == "2 0" ]]; then
    ok "full pipeline scans correctly under hardened runtime (uniform-identity stand-in)"
  else
    bad "hardened full pipeline returned ${RES}"
  fi
else
  bad "skipped — no payload"
fi

head_ "Check 6 — the outer signature seals the onefile payload"
if [[ -n "${PAYLOAD}" ]]; then
  STAGED="$(ls -d "${PWD}"/.bin/opengrep-bundle/bundled/opengrep-*/opengrep 2>/dev/null | tail -1)"
fi
if [[ -n "${STAGED:-}" && -f "${STAGED}" ]]; then
  cp "${STAGED}" "${SCRATCH}/tamper.bin" && chmod +w "${SCRATCH}/tamper.bin"
  if otool -l "${SCRATCH}/tamper.bin" 2>/dev/null | grep -q 'sectname payload'; then
    ok "payload is a Mach-O section covered by the signature"
  else
    bad "no payload section found"
  fi
  codesign --verify --strict "${SCRATCH}/tamper.bin" 2>/dev/null && ok "baseline signature verifies" || bad "baseline does not verify"
  python3 - "${SCRATCH}/tamper.bin" <<'EOF'
import sys
p = sys.argv[1]
b = bytearray(open(p, 'rb').read())
b[int(len(b) * 0.8)] ^= 0xFF
open(p, 'wb').write(bytes(b))
EOF
  TAMPER_VERIFY="$(codesign --verify --strict "${SCRATCH}/tamper.bin" 2>&1 || true)"
  if grep -q 'modified' <<<"${TAMPER_VERIFY}"; then
    ok "flipping one payload byte invalidates the signature"
  else
    bad "tampering was not detected: ${TAMPER_VERIFY}"
  fi
  # Run via a child shell so this shell does not print its own "Killed: 9" notice.
  bash -c '"$1" --version >/dev/null 2>&1' _ "${SCRATCH}/tamper.bin" >/dev/null 2>&1
  TAMPER_RC=$?
  if (( TAMPER_RC == 137 )); then
    ok "kernel refuses to exec the tampered binary (SIGKILL)"
  else
    bad "tampered binary was not killed (rc=${TAMPER_RC})"
  fi
else
  printf '  skipped — no staged binary at .bin/opengrep-bundle/bundled/opengrep-*/opengrep\n'
fi

head_ "Summary"
printf '  %d passed, %d failed\n' "${PASS}" "${FAIL}"
printf '  scratch: %s\n' "${SCRATCH}"
(( FAIL == 0 ))
