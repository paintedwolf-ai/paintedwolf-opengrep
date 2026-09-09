function select({label}, ...rest) { return arguments[1]; }
// ruleid: flow
sink(select({label: 'safe'}, source()));
