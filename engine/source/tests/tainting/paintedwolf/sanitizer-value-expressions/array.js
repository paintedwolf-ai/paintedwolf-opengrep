const row = [typed(), untyped()];
// ok: flow
sink(sanitize(row[0]));
// ruleid: flow
sink(sanitize(row[1]));
