# Painted Wolf Opengrep

The maintained [Opengrep](https://github.com/opengrep/opengrep) engine used by
Painted Wolf Code. This repository owns engine changes, parser inputs, regression
contracts, native builds, and release artifacts. Product rules stay with their
consumer. It builds independently of the Painted Wolf Code repository.

The current source package is `engine/`. Its `source-lock.json` fixes the upstream
revision, ordered patches, grammar revisions, and every engine build input.
Do not change those bytes without rebuilding and qualifying a new revision.

The current version is defined in [the source lock](engine/source-lock.json), based on upstream 1.30.0.
It retains upstream's PHP syntax/matching improvements and propagator-order
correction, and expands ordinary JavaScript and Python behavior: argument binding,
callable dependencies, collection updates, exception completion, and recursive
helper analysis. Qualification includes the retained upstream regressions and
paired controls for these maintained changes.

The source lock binds the version, ordered changes, and complete build inputs.
Each published executable must pass the full frozen qualification for those exact
inputs; a development replay does not qualify different source bytes or an older
executable.

The build derives the CLI, Python package, and native core versions from the
source lock before archiving or compiling the prepared sources. Version changes
do not require edits to version literals in the patch series. The packaged CLI
must report the exact selected version before native qualification begins.

## Build and test

Install Go 1.26.6 or newer for the pinned Task bootstrap and Python 3.9 or newer
for tooling. Native builds currently require macOS arm64, Xcode command-line
tools, Node.js 26.3.0, opam, and pkgconf (`brew install opam pkgconf`). Native
libraries and the private Python runtime come from verified source/runtime pins.
Linux packaging is next; Windows engine builds and execution are future work.

```sh
./task check
./task test
./task build -- --jobs 2
```

The build prints its qualified artifact directory. It uses `.cache/artifacts` by
default; `OPENGREP_CACHE_DIR` selects another location. Build inputs are captured
before work starts. Failed builds retain their directory and log; retry with
`./task build -- --retry-failed`. Do not reuse unfinished build directories.

To admit an already-built artifact without another build:

```sh
./task build -- --seed /absolute/path/to/artifact --no-build
```

Admission validates executable and payload hashes, frozen source membership,
engine contracts, platform checks, and signing provenance. To rerun the complete
engine contract corpus explicitly (the task provisions its locked YAML dependency
in a private `.cache/` virtual environment):

```sh
./task contracts -- /absolute/path/to/opengrep
```

## Recover qualification of a completed build

When native compilation and standalone packaging completed but qualification
failed, rerun qualification without rebuilding or changing the executable:

```sh
./task qualify -- \
  --build-directory /absolute/path/to/completed/work \
  --output /absolute/path/to/new-qualified-artifact \
  --signing-profile /absolute/path/to/signing-profile.json
./task build -- --seed /absolute/path/to/new-qualified-artifact --no-build
```

The build directory must contain its original frozen inputs, source archive,
source trees, standalone distribution, private Python, and platform/runtime
records. Qualification checks them against the current source lock, verifies the
executable against its original platform record, and inspects fresh runtime
extraction and signatures. It reruns **every frozen contract** in a private,
neutral temporary directory before ordinary artifact admission. It does not reuse
individual passing cases or change the declared signing profile.

The original build and failed reports remain untouched. New failures retain their
workspace and full report for inspection; success writes to a new output
directory. Interruption stops the owned verifier and lets its scanner cleanup run.
Fresh builds also use a neutral `work/` directory so directory-selection fixtures
do not inherit the scanner's default `build/` exclusion.

## Package a release

```sh
./task release-pack -- \
  --artifact /absolute/path/to/qualified-artifact \
  --output /absolute/path/to/new-release-directory \
  --tag "$RELEASE_TAG" --channel stable
```

Set `RELEASE_TAG` to `v` followed by the exact version in the finalized
`engine/source-lock.json`; use a new, unpublished tag. Packaging verifies the
artifact against a frozen input snapshot and checks the executable's native
signature before producing a deterministic archive and `release.json`. It does
not rebuild, resign, commit, or publish anything. Output directories must be new.

The archive has nine flat regular files: `opengrep`, `source-lock.json`,
`provenance.json`, `opengrep-source.tar.gz`, `LICENSE`, `contracts.jsonl`,
`platform-checks.json`, `runtime.json`, and `NOTICES-opengrep.md`. `release.json`
records the engine/source identity and the URL, SHA-256, and size of that archive.
The compressed archive and each member are limited to 512 MiB; the expanded tar,
including headers and padding, is limited to 2 GiB. Packaging rejects oversized
outputs before publishing the output directory. Consumers must pin the archive
before extracting it. Notices are checked against the versioned license inventory
and authenticated by the archive pin.

Ad-hoc builds are explicitly **prereleases**. A stable release requires a
Developer ID profile and native signature validation. To build with that profile,
export the public signing certificate as DER, then run:

```sh
python3 engine/signing/signing.py profile --certificate signer.der --output signer.json
export OPENGREP_SIGNING_PROFILE="$PWD/signer.json"
export OPENGREP_SIGN_IDENTITY='Developer ID Application: Your organization (TEAMID)'
./task build -- --jobs 2
```

The certificate's private key must already be available to `codesign`. Signing
happens during the native build, before provenance is produced; ad-hoc and
Developer ID caches have distinct identities. Do not sign the final artifact in
place. Developer ID qualification does not itself claim Apple notarization.
Signing changes the executable and its provenance: when credentials become
available, build a new engine revision and version tag. An already published
ad-hoc prerelease must remain ad-hoc; do not replace its assets or relabel it stable.

The manual `Native release` workflow uses GitHub's [macOS arm64 runner](https://docs.github.com/en/actions/reference/runners/github-hosted-runners),
checks the source and tests, builds or validates a native cache, and publishes a
draft release for review. Run it at an existing version tag with no release or
draft yet, for example:

```sh
gh workflow run native-release.yml --ref "$RELEASE_TAG" -f channel=stable
```

Stable mode uses `APPLE_CERTIFICATE` (base64 PKCS#12 exported from Keychain Access),
`APPLE_CERTIFICATE_PASSWORD`, and `APPLE_SIGNING_IDENTITY` repository secrets (or
organization secrets granted to this repository). Set
the identity to the complete certificate name, such as `Developer ID Application:
Your organization (TEAMID)`. The workflow imports the PKCS#12 with Apple's
`security` tool and reads the public certificate from that keychain, avoiding
[OpenSSL's legacy PKCS#12 cipher incompatibility](https://docs.openssl.org/3.5/man1/openssl-pkcs12/).
Prerelease builds need no signing credentials. To validate the credentials before
starting an engine build, dispatch the same workflow on `main`:

```sh
gh workflow run native-release.yml --ref main -f operation=check-signing
```

This operation imports the key, compiles and signs the small native signature
inspector with hardened runtime and a secure timestamp, and verifies its exact
certificate and Team ID using the release signing policy. It requires no version
tag, does not access the artifact cache or build the engine, and publishes no
release. The temporary signing keychain is removed even if validation fails.

A failed upload can leave a draft. The workflow refuses an existing release or
draft before building and never overwrites its assets. Inspect a partial draft
and finish uploading the exact qualified files, or explicitly delete that
unpublished draft before retrying the workflow. Published releases and their tags
stay unchanged. Each GitHub-hosted job has a [six-hour limit](https://docs.github.com/en/actions/reference/limits);
a cold native build that exceeds it needs local qualification. Only complete,
verified artifacts are cached; unfinished build directories are not resumed.

Publish the reviewed draft only after the exact signed artifact passes its frozen
contracts and payload verification. Portable CI checks packaging only and does
not claim Linux engine support. A Linux development replay can exercise semantics
without qualifying the macOS release's executable, signing, or deployment target.

## Analysis qualification

Engine contracts exercise supported behavior and explicit analysis limitations.
Consumer evaluations also need real framework boundaries and paired vulnerable
and safe helper calls: detecting a direct sink does not demonstrate propagation
through a helper, and reporting a dead closure is a false positive.

Intrafile analysis can resolve same-file helpers, callbacks, and recursive
summaries. It does not establish arbitrary cross-file or dynamic runtime behavior.
Guarded signatures are a separate rule option, `guarded_taint_signatures`; compare
their precision and resource use separately from enabling intrafile analysis.
Neither option changes a consumer's default unless its selected configuration
changes.

Analysis limits produce structured partial-semantics diagnostics while preserving
supported findings. An empty finding list with a partial diagnostic is incomplete
analysis. Qualification must distinguish an expected limitation from a regression,
and must not discard a warning merely because another path found the expected
sink. Recursive calls need a valid summary or an explicit limitation when bounded
contextual analysis cannot continue. Preliminary summary construction must not
leak provisional limits into an otherwise complete final analysis.

## Licensing

The engine retains its upstream [LGPL-2.1 license](LICENSE). Bundled dependency
notices and corresponding-source obligations are in
[`engine/licensing/`](engine/licensing/). Every release carries the modified
engine source, frozen build inputs, retained dependency sources, and notices.
