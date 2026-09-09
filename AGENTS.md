# Painted Wolf Opengrep agent policy

Use `./task` from the repository root for builds and tests. Run `./task check`
and `./task test` before handing off packaging changes; run the frozen contracts
when changing engine behavior. Native builds are expensive: coordinate before
starting another build and allow tests time under host contention.

`engine/source-lock.json` binds engine inputs byte for byte. Preserve the lock
and every listed file together. A changed engine input requires a new reviewed
source revision and build; never relabel an existing artifact. Packaging and
release tooling outside that lock may change without rebuilding the engine.

Keep the repository independent of Painted Wolf Code. It owns the maintained
engine, contracts, build inputs, source retention, and release artifacts. Product
rules and scanner presentation belong to the consuming application.

macOS arm64 is the current native build target. Linux is next; Windows engine
builds and execution are future work. Do not invent unsupported platform assets.

Never remove another agent's work, stash the shared tree, or stop a process you
did not start. Commit or publish only when explicitly authorized. Validate the
complete artifact before packaging, sign before computing provenance, and keep
ad-hoc prereleases distinct from Developer ID releases. Do not add compatibility
shims or migrations for internal pre-v1 structures.
