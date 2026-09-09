function factory() { if (flag) return unknownFactory(); return () => "safe"; }
const helper = factory();
// ruleid: closure-context
sink(helper(source()));
