function select(value = arguments[1]) { return value; }
// ruleid: flow
sink(select(undefined, source()));
