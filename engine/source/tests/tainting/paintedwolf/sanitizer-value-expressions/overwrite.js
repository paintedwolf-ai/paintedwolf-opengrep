const row = {value: typed()};
row.value = untyped();
// ruleid: flow
sink(sanitize(row.value));
