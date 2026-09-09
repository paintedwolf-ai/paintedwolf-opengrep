const [, ...rest] = [source(), "fixed"];
// ok: flow
sink(rest[0]);
