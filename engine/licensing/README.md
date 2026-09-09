# Engine licence inventory

Everything inside the maintained scanner executable, matched to a licence read
from the exact bytes the build consumes.

The generated [inventory](INVENTORY.md), [notices](NOTICES-opengrep.md), and
[source contents](SOURCE-OFFER.md) describe the current package.

## Running it

```
python3 inventory.py collect     # network: refresh evidence from primary sources
python3 inventory.py collect-python  # network: refresh only locked Python distributions
python3 inventory.py build       # offline: inventory.json + INVENTORY.md
python3 inventory.py check       # offline: verify every digest, and that the locks agree
python3 inventory.py notices     # offline: NOTICES-opengrep.md
python3 inventory.py retained-lock  # offline: locks/corresponding-source.json
python3 inventory.py archive-audit
python3 inventory.py verify-artifact <standalone-dist>
```

`collect` and `collect-python` touch the network. Both take a `--cache
<dir>` to reuse downloaded archives across runs. Everything else runs offline
from `evidence/` and `evidence-lock.json`, so a reviewer reproduces the
conclusions without trusting the machine that collected them.

## Where the components come from

`sources.py` derives the component list from the package locks alone:

| Input | Contributes |
|---|---|
| `source-lock.json` | engine revision, interface revision, the four native grammars |
| `engine-submodules.json` | the 40 engine submodules at their pinned revisions |
| `engine-opam/*.opam` | the engine's own runtime dependency declarations |
| `locks/macos-arm64.opam.export` | the OCaml switch, with each package's source archive and checksum |
| `locks/runtimes.json` | the private native C libraries and the Python runtime |
| `locks/dependencies.json`, `locks/python.txt`, `locks/python-bootstrap.txt` | exact Python distribution bytes and runtime/build-only classification |

`engine-submodules.json` and `engine-opam/` are snapshots of the engine at
`acf67b45`, committed so the enumeration runs without a clone. `inventory.py
check` fails if the switch export and the evidence lock stop agreeing.

## Why licence files and not metadata

Package metadata is a claim; the licence file in the distributed source is the
licence. Two cases in this switch where they differ, both of which would have
produced a wrong answer:

- `ocamlgraph 2.2.0` declares `LGPL-2.1-only` in opam. Its LICENSE, in the same
  tarball, carries the OCaml linking exception — believing opam would have
  invented a relink duty that does not exist.
- `menhir 20230608` declares `GPL-2.0-only`. Its LICENSE splits the tree: the
  GPL-2.0 half is the generator, which runs at build time, and the half that
  links is LGPL-2.0 with a linking exception — believing opam would have
  reported the product as GPL.

`classify.py` reads the text, recognising exception clauses before their base
licence so an exception is never dropped. Where a licence file alone does not
settle it — a fork that shipped none, a dual grant stated in a README, a work
that rides inside another component — `determinations.json` records the
conclusion together with the primary source it rests on. Anything still
unresolved stays `undetermined` and shows up as such in `INVENTORY.md`.

## What the build consumes

The build freezes its inputs, so it cannot read this directory. `retained-lock`
writes the one decision the build needs — which upstream sources must travel
with the product — into `locks/corresponding-source.json`, which the package
inventory already covers. `build_support/corresponding_source.py` fetches those
entries and verifies each against the digest its pin records. Re-run
`retained-lock` after `build`, and refresh `source-lock.json` afterwards.

## What is derived rather than measured

Linkage for the OCaml layer is the runtime dependency closure of the engine's
own opam packages, so it over-approximates: a package that a native macOS build
never links still appears if an engine package declares it without a test
filter (`js_of_ocaml` arrives this way). Which Python extension modules Nuitka
keeps is likewise a property of a build. `verify-artifact` reconciles both
against a real standalone distribution. The inventory alone does not establish
which modules a particular binary contains.
