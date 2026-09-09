function factory() { if (flag) return () => "safe"; return unknownFactory(); }
const helper = factory();
// ruleid: closure-context
sink(helper(source()));
