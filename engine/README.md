# Engine source package

`source-lock.json` binds the upstream engine and interface revisions, the ordered
patch series, grammar inputs, and every local build input. Its `upstream_version`
and `patch_version` define the release version. Build and release commands live in the
[repository README](../README.md). Upstream 1.30.0 supplies PHP parsing improvements
and the propagator destination-order correction.

`build.py` verifies and snapshots these inputs before fetching the pinned upstream
sources, applying `patches/series.json`, generating parsers, and building an
isolated OCaml switch and Python CLI. macOS libraries and Python runtime inputs
are pinned in `locks/`; the onefile CLI includes the engine and language catalog.
The build checks Mach-O dependencies and deployment targets, signs the packaged
images before recording provenance, runs the engine contracts, and emits the
corresponding-source archive. The macOS deployment target is 13.0; inspecting that
target does not establish execution qualification on every macOS version.

`artifact.py` admits complete qualified artifacts into a cache keyed by source
lock, native platform, and signing profile. It rejects mismatched or corrupt
payloads. Concurrent callers share one build attempt; failed attempts retain their
logs and require an explicit retry. Admission checks the complete source archive,
payload hashes, contract results, platform records, and signing provenance.

`source/tests/` contains positive, negative, trace, and expected-gap engine
contracts. `verify.py` runs them with one scanner worker and no per-rule wall
timer. Whole-process deadlines scale with observed host contention or an explicit
`PW_TEST_TIMEOUT_SCALE` from 1 through 4. Timeout cleanup owns the started process
group; malformed output and incomplete scans fail qualification. Contract reports
retain effective deadlines, host capacity, commands, and failure output.

`source/` contains maintained parser and analysis overlays. `patches/` contains
engine and interface changes, with dependencies recorded in the ordered series.
Language behavior includes import provenance, lexical shadowing, taint and alias
state, argument binding, expression lowering, and translation of labeled rules.
The contract corpus records the supported behavior and expected gaps; product
rules and product scan evaluations belong to the consuming repository.

This revision extends JavaScript function arguments, callable and method
resolution, computed properties, deletion, and array updates, together with Python
keyword binding, ordered dictionary copies, returned closures, and exception
completion. Paired contracts cover safe overwrites, unused inputs, replaced or
uncalled functions, and recursion that changes its argument before reaching a
sink. Native releases qualify the complete frozen corpus against the executable;
individual passing fixtures do not establish release readiness.

Intrafile helper summaries and guarded signatures are distinct analysis options.
Collection shapes, aliases, recursive contexts, and exception paths remain
bounded. Unsupported constructs or exhausted limits produce structured partial
diagnostics, not a claim of clean coverage. For example, implicit JavaScript
`arguments` handling distinguishes strict/unmapped capture from unsupported
sloppy mapped alias operations; it must not invent snapshot-derived findings when
those aliases are unresolved. Preliminary summary extraction and final call-site
analysis have different diagnostic lifetimes: only the latter can establish that
a contextual recursion limit remains unresolved.

Python intrafile closure analysis preserves lexical local, outer-parameter, and
enclosed bindings by their resolved identity. Returning or storing a closure does
not execute it; later calls observe sibling writes to the same activation's
captured variables, including updates before an exception. Separate factory
activations remain distinct within the precision limits. Activation paths retain
at most 16 call sites and each flow environment retains at most 256 precise
activation frames, including after branch joins. Loop allocations and overflow
use shared state with conservative updates; a call that depends on reduced
precision reports `closure_call_limit` while retaining possible source flows.
Contextual binding handles positional, named, and positional-rest arguments.
Unresolved defaults or keyword-mapping binding use the existing signature result
and report the limitation instead of claiming exact captured-state execution.

`licensing/` holds the versioned dependency inventory and notices. Each release
includes the modified engine sources, locked build inputs, retained dependency
sources, source manifests, and license payloads. Source pins do not by themselves
claim byte-for-byte reproducible executables.
