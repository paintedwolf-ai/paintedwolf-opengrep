# Upstream 1.30 regressions

Source fixtures and the C propagator rule are copied without modification from
[Opengrep v1.30.0](https://github.com/opengrep/opengrep/tree/acf67b45c97c4b63626536605c77064ef536806d),
under its retained [LGPL-2.1 license](LICENSE).

`php-patterns/` retains the sources from `tests/patterns/php/`; each matching
upstream `.sgrep` pattern is preserved as the pattern string in its YAML rule.
The upstream `//ERROR:` comments identify required matches; unmarked alternatives
must remain quiet. `php-parsing/` retains changed `tests/parsing/php/` inputs and
uses a nonmatching search rule to require a complete parse without diagnostics.
`propagators/` retains `tests/taint_maturity/c/taint_propagator.{c,yaml}`, exercising
both argument orders and the clean control. Every pair is discovered by the
normal frozen contract runner.
