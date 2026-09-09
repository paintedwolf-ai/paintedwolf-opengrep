# Inventory — opengrep 1.30.0+paintedwolf.32

Upstream `https://github.com/opengrep/opengrep.git` at `acf67b45c97c4b63626536605c77064ef536806d`.

316 components inventoried; 288 link into or ship inside the executable and the rest are build-only or virtual opam packages.

Licence conclusions come from the licence file inside the exact pinned source, not from package metadata. Run `inventory.py check` to verify every digest offline.

The OCaml layer's linkage is the runtime dependency closure of the engine's own opam packages. That over-approximates: a package a native build never links still appears here if an engine package declares it without a test filter. `inventory.py verify-artifact` narrows it against a real artefact.

## engine (1)

| component | licence | linkage | obligations |
|---|---|---|---|
| `opengrep` | LGPL-2.1 | static | notice, license-text, source-offer, relink |

## parsers (40)

| component | licence | linkage | obligations |
|---|---|---|---|
| `cli_src_semgrep_semgrep_interfaces` | **undetermined** | static | — |
| `languages_apex_tree-sitter_semgrep-apex` | MIT | static | notice, license-text |
| `languages_bash_tree-sitter_semgrep-bash` | MIT | static | notice, license-text |
| `languages_cairo_tree-sitter_semgrep-cairo` | MIT | static | notice, license-text |
| `languages_circom_tree-sitter_semgrep-circom` | MIT | static | notice, license-text |
| `languages_cpp_tree-sitter_semgrep-cpp` | MIT | static | notice, license-text |
| `languages_crystal_tree-sitter_opengrep-crystal` | MIT | static | notice, license-text |
| `languages_csharp_tree-sitter_semgrep-c-sharp` | MIT | static | notice, license-text |
| `languages_dart_tree-sitter_semgrep-dart` | MIT | static | notice, license-text |
| `languages_dockerfile_tree-sitter_semgrep-dockerfile` | MIT | static | notice, license-text |
| `languages_elixir_tree-sitter_semgrep-elixir` | Apache-2.0 | static | notice, license-text |
| `languages_go_tree-sitter_semgrep-go` | MIT | static | notice, license-text |
| `languages_hack_tree-sitter_semgrep-hack` | MIT | static | notice, license-text |
| `languages_html_tree-sitter_semgrep-html` | MIT | static | notice, license-text |
| `languages_java_tree-sitter_semgrep-java` | MIT | static | notice, license-text |
| `languages_jsonnet_tree-sitter_semgrep-jsonnet` | MIT | static | notice, license-text |
| `languages_julia_tree-sitter_semgrep-julia` | MIT | static | notice, license-text |
| `languages_kotlin_tree-sitter_semgrep-kotlin` | MIT | static | notice, license-text |
| `languages_lisp_tree-sitter_semgrep-clojure` | CC0-1.0 | static | notice, license-text |
| `languages_lua_tree-sitter_semgrep-lua` | MIT | static | notice, license-text |
| `languages_move_on_aptos_tree-sitter_semgrep-move-on-aptos` | Apache-2.0 | static | notice, license-text |
| `languages_move_on_sui_tree-sitter_semgrep-move-on-sui` | MIT | static | notice, license-text |
| `languages_ocaml_tree-sitter_semgrep-ocaml` | MIT | static | notice, license-text |
| `languages_php_tree-sitter_semgrep-php` | MIT | static | notice, license-text |
| `languages_promql_tree-sitter_semgrep-promql` | Apache-2.0 | static | notice, license-text |
| `languages_protobuf_tree-sitter_semgrep-proto` | MIT | static | notice, license-text |
| `languages_python_tree-sitter_semgrep-python` | MIT | static | notice, license-text |
| `languages_ql_tree-sitter_semgrep-ql` | MIT | static | notice, license-text |
| `languages_r_tree-sitter_semgrep-r` | MIT | static | notice, license-text |
| `languages_ruby_tree-sitter_semgrep-ruby` | MIT | static | notice, license-text |
| `languages_rust_tree-sitter_semgrep-rust` | MIT | static | notice, license-text |
| `languages_solidity_tree-sitter_semgrep-solidity` | MIT | static | notice, license-text |
| `languages_swift_tree-sitter_semgrep-swift` | MIT | static | notice, license-text |
| `languages_terraform_tree-sitter_semgrep-hcl` | Apache-2.0 | static | notice, license-text |
| `languages_typescript_tree-sitter_semgrep-tsx` | MIT | static | notice, license-text |
| `languages_typescript_tree-sitter_semgrep-typescript` | MIT | static | notice, license-text |
| `libs_ocaml-tree-sitter-core` | LGPL-2.1 | static | notice, license-text, source-offer, relink |
| `libs_pcre2` | LGPL-2.1 WITH OCaml-LGPL-linking-exception | static | notice, license-text, source-offer |
| `libs_testo` | ISC | static | notice, license-text |
| `tests_semgrep-rules` | LGPL-2.1 AND Commons-Clause | build-only | — |

## grammars (4)

| component | licence | linkage | obligations |
|---|---|---|---|
| `groovy` | MIT | static | notice, license-text |
| `perl` | MIT | static | notice, license-text |
| `powershell` | MIT | static | notice, license-text |
| `scheme` | MIT | static | notice, license-text |

## ocaml (222)

| component | licence | linkage | obligations |
|---|---|---|---|
| `ANSITerminal-0.8.5` | LGPL-3.0 WITH OCaml-LGPL-linking-exception | static | notice, license-text, source-offer |
| `alcotest-1.9.1` | ISC | static | notice, license-text |
| `alcotest-js-1.9.1` | ISC | static | notice, license-text |
| `alcotest-lwt-1.9.1` | ISC | static | notice, license-text |
| `ambient-context-0.2` | MIT | static | notice, license-text |
| `ambient-context-lwt-0.2` | MIT | static | notice, license-text |
| `angstrom-0.16.1` | BSD-3-Clause | static | notice, license-text |
| `arp-3.1.1` | ISC | static | notice, license-text |
| `asn1-combinators-0.2.6` | ISC | static | notice, license-text |
| `astring-0.8.5` | ISC | static | notice, license-text |
| `atd-2.16.0` | BSD-3-Clause | static | notice, license-text |
| `atdgen-2.16.0` | BSD-3-Clause | static | notice, license-text |
| `atdgen-runtime-2.16.0` | BSD-3-Clause | static | notice, license-text |
| `awa-0.3.0` | ISC | static | notice, license-text |
| `awa-mirage-0.3.0` | ISC | static | notice, license-text |
| `backoff-0.1.1` | ISC | static | notice, license-text |
| `base-bigarray-base` | **undetermined** | virtual | — |
| `base-bytes-base` | **undetermined** | virtual | — |
| `base-domains-base` | **undetermined** | virtual | — |
| `base-effects-base` | **undetermined** | virtual | — |
| `base-nnp-base` | **undetermined** | virtual | — |
| `base-threads-base` | **undetermined** | virtual | — |
| `base-unix-base` | **undetermined** | virtual | — |
| `base-v0.17.3` | MIT | static | notice, license-text |
| `base64-3.5.2` | ISC | static | notice, license-text |
| `bigstringaf-0.10.0` | BSD-3-Clause | static | notice, license-text |
| `biniou-1.2.2` | BSD-3-Clause | static | notice, license-text |
| `bos-0.3.0` | ISC | static | notice, license-text |
| `ca-certs-0.2.3` | ISC | static | notice, license-text |
| `ca-certs-nss-3.101` | ISC | static | notice, license-text |
| `calendar-3.0.0` | LGPL-2.1 WITH OCaml-LGPL-linking-exception | static | notice, license-text, source-offer |
| `camlp-streams-5.0.1` | LGPL-2.1 WITH OCaml-LGPL-linking-exception | static | notice, license-text, source-offer |
| `carton-0.7.2` | ISC | static | notice, license-text |
| `carton-git-0.7.2` | ISC | static | notice, license-text |
| `carton-lwt-0.7.2` | ISC | static | notice, license-text |
| `checkseum-0.5.3` | MIT | static | notice, license-text |
| `cmdliner-2.1.1` | ISC | static | notice, license-text |
| `cohttp-6.0.0` | ISC | static | notice, license-text |
| `cohttp-lwt-6.0.0` | ISC | static | notice, license-text |
| `cohttp-lwt-unix-6.0.0` | ISC | static | notice, license-text |
| `compiler-cloning-disabled` | **undetermined** | virtual | — |
| `conduit-6.2.3` | ISC | static | notice, license-text |
| `conduit-lwt-6.2.3` | ISC | static | notice, license-text |
| `conduit-lwt-unix-6.2.3` | ISC | static | notice, license-text |
| `conf-gmp-5` | **undetermined** | build-only | — |
| `conf-gmp-powm-sec-4` | **undetermined** | build-only | — |
| `conf-libev-4-13` | **undetermined** | build-only | — |
| `conf-pkg-config-5` | **undetermined** | build-only | — |
| `cppo-1.8.0` | BSD-3-Clause | build-only | — |
| `csexp-1.5.2` | MIT | static | notice, license-text |
| `cstruct-6.2.0` | ISC | static | notice, license-text |
| `cstruct-lwt-6.2.0` | ISC | static | notice, license-text |
| `cstruct-unix-6.2.0` | ISC | static | notice, license-text |
| `ctypes-0.24.0` | MIT | static | notice, license-text |
| `decompress-1.6.0` | MIT | static | notice, license-text |
| `digestif-1.3.1` | MIT | static | notice, license-text |
| `dns-7.0.3` | BSD-2-Clause | static | notice, license-text |
| `dns-client-7.0.3` | BSD-2-Clause | static | notice, license-text |
| `dns-client-lwt-7.0.3` | BSD-2-Clause | static | notice, license-text |
| `dns-client-mirage-7.0.3` | BSD-2-Clause | static | notice, license-text |
| `domain-local-await-1.0.1` | ISC | static | notice, license-text |
| `domain-name-0.5.0` | ISC | static | notice, license-text |
| `domainslib-0.5.2` | ISC | static | notice, license-text |
| `duff-0.5` | MIT | static | notice, license-text |
| `dune-3.24.2` | MIT | static | notice, license-text |
| `dune-build-info-3.24.2` | MIT | build-only | — |
| `dune-configurator-3.24.2` | MIT | static | notice, license-text |
| `duration-0.3.1` | ISC | static | notice, license-text |
| `easy-format-1.3.4` | BSD-3-Clause | static | notice, license-text |
| `either-1.0.0` | MIT | build-only | — |
| `emile-1.1` | MIT | static | notice, license-text |
| `encore-0.8.1` | MIT | static | notice, license-text |
| `eqaf-0.9` | MIT | static | notice, license-text |
| `ethernet-3.2.0` | ISC | static | notice, license-text |
| `faraday-0.8.2` | BSD-3-Clause | static | notice, license-text |
| `fileutils-0.6.6` | LGPL-2.1 WITH OCaml-LGPL-linking-exception | static | notice, license-text, source-offer |
| `fix-20250919` | LGPL-2.0 WITH OCaml-LGPL-linking-exception | build-only | — |
| `fmt-0.11.0` | ISC | static | notice, license-text |
| `fpath-0.7.3` | ISC | static | notice, license-text |
| `gen-1.1` | BSD-2-Clause | static | notice, license-text |
| `git-3.15.0` | ISC | static | notice, license-text |
| `git-mirage-3.15.0` | ISC | static | notice, license-text |
| `git-paf-3.15.0` | ISC | static | notice, license-text |
| `git-unix-3.15.0` | ISC | static | notice, license-text |
| `gmap-0.3.0` | ISC | static | notice, license-text |
| `h2-0.13.0` | BSD-3-Clause | static | notice, license-text |
| `happy-eyeballs-0.6.0` | ISC | static | notice, license-text |
| `happy-eyeballs-lwt-0.6.0` | ISC | static | notice, license-text |
| `happy-eyeballs-mirage-0.6.0` | ISC | static | notice, license-text |
| `hex-1.5.0` | ISC | static | notice, license-text |
| `hkdf-1.0.4` | BSD-2-Clause | static | notice, license-text |
| `hmap-0.8.1` | ISC | static | notice, license-text |
| `hpack-0.13.0` | BSD-3-Clause | static | notice, license-text |
| `http-6.0.0` | ISC | static | notice, license-text |
| `httpaf-0.7.1` | BSD-3-Clause | static | notice, license-text |
| `httpun-types-0.2.0` | BSD-3-Clause | static | notice, license-text |
| `hxd-0.5.0` | MIT | static | notice, license-text |
| `integers-0.8.0` | MIT | static | notice, license-text |
| `integers_stubs_js-1.0` | MIT | static | notice, license-text |
| `ipaddr-5.6.2` | ISC | static | notice, license-text |
| `ipaddr-cstruct-5.6.2` | ISC | static | notice, license-text |
| `ipaddr-sexp-5.6.2` | ISC | static | notice, license-text |
| `jane-street-headers-v0.17.0` | MIT | static | notice, license-text |
| `js_of_ocaml-6.4.1` | LGPL-2.1 WITH OCaml-LGPL-linking-exception | static | notice, license-text, source-offer |
| `js_of_ocaml-compiler-6.4.1` | LGPL-2.1 WITH OCaml-LGPL-linking-exception | static | notice, license-text, source-offer |
| `jsonrpc-1.22.0` | ISC | static | notice, license-text |
| `jst-config-v0.17.0` | MIT | static | notice, license-text |
| `ke-0.6` | MIT | static | notice, license-text |
| `logs-0.10.0` | ISC | static | notice, license-text |
| `lru-0.3.1` | ISC | static | notice, license-text |
| `lsp-1.22.0` | ISC | static | notice, license-text |
| `lwt-6.1.2` | MIT | static | notice, license-text |
| `lwt-dllist-1.1.0` | MIT | static | notice, license-text |
| `lwt_ppx-6.1.0` | MIT | static | notice, license-text |
| `macaddr-5.6.2` | ISC | static | notice, license-text |
| `macaddr-cstruct-5.6.2` | ISC | static | notice, license-text |
| `magic-mime-1.3.1` | ISC | static | notice, license-text |
| `memprof-limits-dev` | LGPL-3.0 WITH LGPL-3.0-linking-exception | static | notice, license-text, source-offer |
| `menhir-20230608` | GPL-2.0 (generator) AND LGPL-2.0 WITH OCaml-LGPL-linking-exception (lib/, sdk/) | build-only | — |
| `menhirLib-20230608` | LGPL-2.0 WITH OCaml-LGPL-linking-exception | static | notice, license-text, source-offer |
| `menhirSdk-20230608` | LGPL-2.0 WITH OCaml-LGPL-linking-exception | static | notice, license-text, source-offer |
| `metrics-0.5.0` | ISC | static | notice, license-text |
| `mimic-0.0.6` | ISC | static | notice, license-text |
| `mimic-happy-eyeballs-0.0.6` | ISC | static | notice, license-text |
| `mirage-clock-4.2.0` | ISC | static | notice, license-text |
| `mirage-clock-unix-4.2.0` | ISC | static | notice, license-text |
| `mirage-crypto-0.11.3` | ISC | static | notice, license-text |
| `mirage-crypto-ec-0.11.3` | ISC | static | notice, license-text |
| `mirage-crypto-pk-0.11.3` | ISC | static | notice, license-text |
| `mirage-crypto-rng-0.11.3` | ISC | static | notice, license-text |
| `mirage-crypto-rng-lwt-0.11.3` | ISC | static | notice, license-text |
| `mirage-flow-3.0.0` | ISC | static | notice, license-text |
| `mirage-kv-6.1.1` | ISC | static | notice, license-text |
| `mirage-net-4.0.0` | ISC | static | notice, license-text |
| `mirage-random-3.0.0` | ISC | static | notice, license-text |
| `mirage-runtime-4.11.2` | ISC | static | notice, license-text |
| `mirage-time-3.0.0` | ISC | static | notice, license-text |
| `mirage-unix-5.0.1` | ISC | static | notice, license-text |
| `mtime-2.2.0` | ISC | static | notice, license-text |
| `multicore-magic-2.3.2` | ISC | static | notice, license-text |
| `num-1.6` | LGPL-2.1 WITH OCaml-LGPL-linking-exception | static | notice, license-text, source-offer |
| `ocaml-5.5.1` | LGPL-2.1 WITH OCaml-LGPL-linking-exception | static | notice, license-text, source-offer |
| `ocaml-base-compiler-5.5.1` | LGPL-2.1 WITH OCaml-LGPL-linking-exception | static | notice, license-text, source-offer |
| `ocaml-compiler-5.5.1` | LGPL-2.1 WITH OCaml-LGPL-linking-exception | static | notice, license-text, source-offer |
| `ocaml-compiler-libs-v0.17.0` | MIT | static | notice, license-text |
| `ocaml-options-vanilla-1` | **undetermined** | virtual | — |
| `ocaml-syntax-shims-1.0.0` | MIT | static | notice, license-text |
| `ocaml-version-4.1.3` | ISC | build-only | — |
| `ocaml_intrinsics_kernel-v0.17.2` | MIT | static | notice, license-text |
| `ocamlbuild-0.16.1` | LGPL-2.0 WITH OCaml-LGPL-linking-exception | build-only | — |
| `ocamlfind-1.9.9~preview` | MIT | static | notice, license-text |
| `ocamlformat-0.29.0` | MIT | build-only | — |
| `ocamlformat-lib-0.29.0` | MIT | build-only | — |
| `ocamlgraph-2.2.0` | LGPL-2.1 WITH OCaml-LGPL-linking-exception | static | notice, license-text, source-offer |
| `ocolor-1.3.1` | MIT | static | notice, license-text |
| `ocp-indent-1.10.0` | LGPL-2.1 WITH OCaml-LGPL-linking-exception | build-only | — |
| `ocplib-endian-1.2` | LGPL-2.1 WITH OCaml-LGPL-linking-exception | static | notice, license-text, source-offer |
| `optint-0.3.0` | MIT | static | notice, license-text |
| `paf-0.5.0` | MIT | static | notice, license-text |
| `parsexp-v0.17.0` | MIT | static | notice, license-text |
| `pbkdf-1.2.0` | BSD-2-Clause | static | notice, license-text |
| `pecu-0.7` | MIT | static | notice, license-text |
| `ppx_assert-v0.17.0` | MIT | static | notice, license-text |
| `ppx_base-v0.17.0` | MIT | static | notice, license-text |
| `ppx_cold-v0.17.0` | MIT | static | notice, license-text |
| `ppx_compare-v0.17.0` | MIT | static | notice, license-text |
| `ppx_derivers-1.2.1` | BSD-3-Clause | static | notice, license-text |
| `ppx_deriving-6.1.3` | MIT | static | notice, license-text |
| `ppx_deriving_yojson-3.10.0` | MIT | static | notice, license-text |
| `ppx_enumerate-v0.17.0` | MIT | static | notice, license-text |
| `ppx_expect-v0.17.3` | MIT | static | notice, license-text |
| `ppx_globalize-v0.17.2` | MIT | static | notice, license-text |
| `ppx_hash-v0.17.0` | MIT | static | notice, license-text |
| `ppx_here-v0.17.0` | MIT | static | notice, license-text |
| `ppx_inline_test-v0.17.1` | MIT | static | notice, license-text |
| `ppx_optcomp-v0.17.1` | MIT | static | notice, license-text |
| `ppx_sexp_conv-v0.17.1` | MIT | static | notice, license-text |
| `ppx_yojson_conv_lib-v0.17.0` | MIT | static | notice, license-text |
| `ppxlib-0.38.0` | MIT | static | notice, license-text |
| `ppxlib_jane-v0.17.4` | MIT | static | notice, license-text |
| `psq-0.2.1` | ISC | static | notice, license-text |
| `ptime-1.2.0` | ISC | static | notice, license-text |
| `randomconv-0.1.3` | ISC | static | notice, license-text |
| `re-1.14.0` | LGPL-2.1 WITH OCaml-LGPL-linking-exception | static | notice, license-text, source-offer |
| `result-1.5` | BSD-3-Clause | static | notice, license-text |
| `rresult-0.7.0` | ISC | static | notice, license-text |
| `sarif-0.3.1` | MIT | static | notice, license-text |
| `saturn-1.0.0` | ISC | static | notice, license-text |
| `sedlex-3.7` | MIT | static | notice, license-text |
| `semver-0.2.1` | BSD-3-Clause | static | notice, license-text |
| `seq-base` | **undetermined** | virtual | — |
| `sexplib-v0.17.0` | BSD-3-Clause AND MIT | static | notice, license-text |
| `sexplib0-v0.17.0` | MIT | static | notice, license-text |
| `stdio-v0.17.0` | MIT | static | notice, license-text |
| `stdlib-shims-0.3.0` | LGPL-2.1 WITH OCaml-LGPL-linking-exception | static | notice, license-text, source-offer |
| `stringext-1.6.0` | MIT | static | notice, license-text |
| `tcpip-8.0.0` | ISC | static | notice, license-text |
| `terminal_size-0.2.0` | BSD-2-Clause | static | notice, license-text |
| `thread-local-storage-0.2` | MIT | static | notice, license-text |
| `thread-table-1.0.0` | ISC | static | notice, license-text |
| `time_now-v0.17.0` | MIT | static | notice, license-text |
| `timedesc-3.1.2` | MIT | static | notice, license-text |
| `timedesc-tzdb-3.1.2` | MIT | static | notice, license-text |
| `timedesc-tzlocal-3.1.2` | MIT | static | notice, license-text |
| `tls-0.17.3` | BSD-2-Clause | static | notice, license-text |
| `tls-lwt-0.17.3` | BSD-2-Clause | static | notice, license-text |
| `tls-mirage-0.17.3` | BSD-2-Clause | static | notice, license-text |
| `topkg-1.1.1` | ISC | build-only | — |
| `tsort-2.2.0` | MIT | build-only | — |
| `uri-4.4.0` | ISC | static | notice, license-text |
| `uri-sexp-4.4.0` | ISC | static | notice, license-text |
| `uucp-17.0.0` | ISC | static | notice, license-text |
| `uuidm-0.9.10` | ISC | static | notice, license-text |
| `uuseg-17.0.0` | ISC | build-only | — |
| `uutf-1.0.4` | ISC | static | notice, license-text |
| `visitors-20260520` | LGPL-2.1 WITH OCaml-LGPL-linking-exception | static | notice, license-text, source-offer |
| `x509-0.16.5` | BSD-2-Clause | static | notice, license-text |
| `xmlm-1.4.0` | ISC | static | notice, license-text |
| `yaml-3.2.0` | ISC AND MIT | static | notice, license-text |
| `yojson-2.2.2` | BSD-3-Clause | static | notice, license-text |
| `zarith-1.14` | LGPL-2.0 WITH OCaml-LGPL-linking-exception | static | notice, license-text, source-offer |
| `zarith_stubs_js-v0.17.0` | MIT | static | notice, license-text |

## native (6)

| component | licence | linkage | obligations |
|---|---|---|---|
| `gmp` | LGPL-3.0-or-later OR GPL-2.0-or-later | static | notice, license-text, source-offer, relink |
| `libev` | BSD-2-Clause OR GPL-2.0-or-later | static | notice, license-text |
| `pcre` | BSD-3-Clause | static | notice, license-text |
| `pcre2` | BSD-3-Clause WITH PCRE2-exception | static | notice, license-text |
| `tree-sitter` | MIT | static | notice, license-text |
| `zstd` | BSD-3-Clause OR GPL-2.0 | static | notice, license-text |

## python-runtime (5)

| component | licence | linkage | obligations |
|---|---|---|---|
| `cpython` | PSF-2.0 | bundled | notice, license-text |
| `ncurses` | ncurses-X11 | bundled | notice, license-text |
| `openssl` | Apache-2.0 | bundled | notice, license-text |
| `sqlite` | SQLite-public-domain | bundled | notice, license-text |
| `tcl-tk` | TCL | bundled | notice, license-text |

## python (38)

| component | licence | linkage | obligations |
|---|---|---|---|
| `Nuitka` | Apache-2.0 | bundled | notice, license-text |
| `Pygments` | BSD-2-Clause | bundled | notice, license-text |
| `annotated-doc` | MIT | bundled | notice, license-text |
| `attrs` | MIT | bundled | notice, license-text |
| `boltons` | BSD-2-Clause | bundled | notice, license-text |
| `bracex` | MIT | bundled | notice, license-text |
| `certifi` | MPL-2.0 | bundled | notice, license-text, source-offer |
| `charset-normalizer` | MIT | bundled | notice, license-text |
| `click` | BSD-3-Clause | bundled | notice, license-text |
| `click-option-group` | BSD-3-Clause | bundled | notice, license-text |
| `colorama` | BSD-3-Clause | bundled | notice, license-text |
| `face` | BSD-2-Clause | bundled | notice, license-text |
| `glom` | BSD-2-Clause | bundled | notice, license-text |
| `idna` | BSD-3-Clause | bundled | notice, license-text |
| `jaraco.context` | MIT | bundled | notice, license-text |
| `jaraco.functools` | MIT | bundled | notice, license-text |
| `jaraco.text` | MIT | bundled | notice, license-text |
| `jsonschema` | MIT | bundled | notice, license-text |
| `jsonschema-specifications` | MIT | bundled | notice, license-text |
| `markdown-it-py` | MIT | bundled | notice, license-text |
| `mdurl` | MIT | bundled | notice, license-text |
| `more-itertools` | MIT | bundled | notice, license-text |
| `ordered-set` | MIT | bundled | notice, license-text |
| `packaging` | Apache-2.0 OR BSD-2-Clause | bundled | notice, license-text |
| `peewee` | MIT | bundled | notice, license-text |
| `protobuf` | BSD-3-Clause | bundled | notice, license-text |
| `referencing` | MIT | bundled | notice, license-text |
| `requests` | Apache-2.0 | bundled | notice, license-text |
| `rich` | MIT | bundled | notice, license-text |
| `rpds-py` | MIT | bundled | notice, license-text |
| `ruamel.yaml` | MIT | bundled | notice, license-text |
| `shellingham` | ISC | bundled | notice, license-text |
| `typer` | MIT | bundled | notice, license-text |
| `typer-slim` | MIT | bundled | notice, license-text |
| `typing_extensions` | PSF-2.0 | bundled | notice, license-text |
| `urllib3` | MIT | bundled | notice, license-text |
| `wcmatch` | MIT | bundled | notice, license-text |
| `zstandard` | BSD-3-Clause | bundled | notice, license-text |

