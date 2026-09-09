# Corresponding source for the scanner engine

The standalone executable contains a native engine and private runtime. Three of its
licences make the combined work's source availability a condition of shipping
it, and one of those goes further than an offer of source.

## What each licence asks

| Licence | Components | Duty |
|---|---|---|
| LGPL-2.1, no exception | opengrep, `ocaml-tree-sitter-core` | clause 6: the recipient must be able to relink the executable against a modified library |
| LGPL-3.0 | GMP 6.3.0 | clause 4: same relink duty, stated as "Minimal Corresponding Source" plus installation information |
| LGPL with a linking exception | 25 works — 23 OCaml packages including the runtime, `zarith`, `re`, `ocamlgraph`, `menhirLib` and `memprof-limits`, plus the OCaml `pcre2` bindings and `testo` | source availability only; the exception waives the relink duty |
| MPL-2.0 | `certifi` | source form of the covered files |
| Apache-2.0 | 4 grammars, OpenSSL, `requests`, `packaging` | attribution, licence copy, change notices; no source duty |

A relink duty is not satisfied by publishing the engine's own source. The
recipient needs the other side of the link too: the object files or the sources
and build inputs that reproduce them.

## What the archive carries

`engine/build_support/source_archive.py` puts into
`opengrep-source.tar.gz`:

- every tracked file of the engine tree, recursing into its submodules except
  those under a test tree
- the locked source overlays from `engine/source/`
- files created by the declared engine, interface and grammar patches
- the four native grammar trees and their generated parser outputs
- `source-lock.json` and the frozen build inputs
- under `third-party/`, the retained upstream archive for every component that
  owes source, with `RETAINED-SOURCE.json` recording each one's URL, digest and
  which digest it was verified against

The retained set is not decided at build time.
`inventory.py retained-lock` writes it to `locks/corresponding-source.json`
from the inventory, and the package inventory covers that file, so the build
reads a frozen decision. `build_support/corresponding_source.py` fetches each
entry and refuses any whose bytes do not match the pin.

Permissive inputs are not retained. MIT, ISC, BSD and Apache ask for
attribution, which `NOTICES-opengrep.md` gives, not for source.

## What is still not carried

`ocaml` and `ocaml-base-compiler` are opam meta-packages with no distribution
of their own; the OCaml runtime source is the `ocaml-compiler` tarball, which
is retained.

`tests/semgrep-rules` is deliberately absent. Its 4,008 files are a test
corpus, reach no binary, and carry a Commons Clause condition that withholds
the right to sell software whose value derives substantially from them.

`inventory.py archive-audit` reports the state of both.
