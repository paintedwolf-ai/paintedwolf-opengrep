const row = {value: typed(), unknown: untyped()};
// ok: flow
sink(sanitize(row.value));
// ruleid: flow
sink(sanitize(row.unknown));
