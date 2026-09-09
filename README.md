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

Local source builds produce ad-hoc development artifacts. Stable releases use the
committed [Developer ID policy](engine/signing/release-profile.json): exact Apple
Team ID and leaf certificate SHA-256, hardened runtime, secure timestamps, and no
entitlements on every native image. Certificate rotation is a reviewed policy
change followed by a new engine revision. Developer ID signing does not itself
claim Apple notarization; Painted Wolf Code notarizes its complete application.

The manual `Native release` workflow uses fresh GitHub-hosted macOS arm64 runners.
Run it at the exact version tag on a commit already reachable from `main`, with no
existing release or draft:

```sh
gh workflow run native-release.yml --ref "$RELEASE_TAG" -f operation=build
```

The workflow verifies tag, source commit, workflow commit and repository identity
before building. Its isolated stages are:

1. Compile and qualify an ad-hoc engine, without Apple credentials or write tokens.
2. Import the approved certificate in the protected `signing` environment; sign
   embedded images without running artifact code or a compiler; delete the keychain.
3. Use the hash-pinned Nuitka compressor and bootstrap compiler on a fresh runner
   to package those signed bytes without signing credentials.
4. Sign the outer executable in another protected signing job, then remove the key.
5. On a fresh runner, verify native signatures and platform dependencies, run every
   frozen contract against the final executable, and regenerate qualification facts.
6. In the protected `release` environment, verify the artifact again, attest the
   archive, descriptor and build evidence, and create a complete draft.

Jobs exchange bounded, digest-checked handoffs through immutable Actions artifact
IDs from the same run and attempt. No completed engine cache is reused for a
release. Python distributions and bootstrap tools are downloaded by exact URL,
size and SHA-256, then installed offline with hashes and no dependency resolution.
Grammar generators are pinned as both compressed archives and executable bytes.
The complete opam switch imports against an empty local repository with required
checksums. Runner image and compiler/tool versions are recorded in build evidence;
the hosted image and system toolchain are not claimed to be reproducible.

Only the publication job has `contents: write`, `id-token: write` and
`attestations: write`. Its GitHub artifact attestation binds the reviewed source
and workflow commit; build evidence separately identifies the earlier compile job
and unsigned handoff. This is provenance, not a claim of byte-for-byte
reproducibility or formal SLSA certification.

Configure `APPLE_CERTIFICATE` (base64 PKCS#12), `APPLE_CERTIFICATE_PASSWORD`, and
`APPLE_SIGNING_IDENTITY` as secrets of the `signing` environment. The identity is
the complete `Developer ID Application: ... (TEAMID)` name. The workflow imports
the PKCS#12 using Apple's `security` tool and refuses a certificate that differs
from the committed policy. To check credentials without building, use a version
tag whose source is already on `main` (it may already have a release):

```sh
gh workflow run native-release.yml --ref "$RELEASE_TAG" -f operation=check-signing
```

This operation compiles the trusted inspector before importing the key, signs it,
and verifies its exact certificate, Team ID, hardened runtime and timestamp. It
publishes no release. The temporary keychain is removed even if validation fails.

A failed upload can leave a draft. The workflow refuses an existing release or
draft before building and never overwrites its assets. Inspect a partial draft;
delete an unpublished failed draft before retrying if necessary. Rerun **all
jobs**: a later attempt may not reuse an earlier attempt's build handoff. Published
immutable releases and their tags stay unchanged. Each GitHub-hosted job has a
[six-hour limit](https://docs.github.com/en/actions/reference/limits); a timeout
requires a build performance fix or an explicitly redesigned pipeline, not a
locally built substitute with a new hosted-build attestation.

Publish the reviewed draft only after the exact signed artifact passes its frozen
contracts and payload verification. The draft must contain exactly the archive,
`release.json`, `build-evidence.json`, and `provenance.sigstore.json`. Immutable
releases must be enabled **before** publication. GitHub creates a separate release
attestation when the draft is published; new consumer selection verifies both the
workflow provenance and immutable-release membership. Portable CI checks packaging only and does
not claim Linux engine support. A Linux development replay can exercise semantics
without qualifying the macOS release's executable, signing, or deployment target.

## GitHub release controls

In Settings → Environments, create `signing` and `release`. Enable **Required
reviewers**, select the release operator, leave **Prevent self-review** unchecked,
and disable administrator bypass. Under **Selected branches and tags**, add a
**Tag** rule for `v*` (no branch rule). Move the three Apple secrets
to `signing` and revoke this repository's access to their organization-level
copies; environment secrets alone do not remove broader secret access.

In Settings → Rules → Rulesets, activate a `main` branch ruleset requiring pull
requests and the `check` status from GitHub Actions; block deletion and force
pushes. Set required PR approvals to zero for this single-maintainer repository.
For `v*`, use a tag-integrity ruleset restricting updates and deletions with no
bypass actors. Use a separate tag-creation ruleset restricting creations, with
only the release operator's role/team allowed to bypass that creation rule.
Separating them prevents permission to create a tag from also allowing it to be
rewritten. Keep immutable releases enabled. These controls complement the
in-workflow checks; merely naming an environment in YAML does not configure its
protection rules. See GitHub's [environment controls](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments)
and [available rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets).

After publishing a new immutable release, select it in Painted Wolf Code using
the exact tag and independently reviewed full producer commit. Commit its pin and
retained attestation evidence together. Ordinary local builds continue to use the
checked-in pin and verified cache without GitHub access or engine compilation.

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
