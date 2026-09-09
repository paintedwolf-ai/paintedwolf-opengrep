const row = {value: typed()}; const alias = row;
// ok: flow
sink(sanitize(alias.value));
alias.value = untyped();
// ruleid: flow
sink(sanitize(row.value));
