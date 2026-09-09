function factory() { if (flag) return value => "safe"; return unknownFactory(); }
const helper = factory();
// ruleid: closure-context
sink(helper(source()));
