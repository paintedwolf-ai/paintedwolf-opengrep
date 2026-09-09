function select(first, ...tail) { return arguments[0]; }
// ok: flow
sink(select('safe', source()));
