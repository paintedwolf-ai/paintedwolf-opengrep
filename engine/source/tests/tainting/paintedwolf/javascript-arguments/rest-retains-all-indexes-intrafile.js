function select(first, ...tail) { return arguments[1]; }
// ruleid: flow
sink(select('safe', source()));
