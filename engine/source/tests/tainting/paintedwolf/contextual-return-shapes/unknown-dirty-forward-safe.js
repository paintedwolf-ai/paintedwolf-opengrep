function factory() { if (flag) return () => source(); return unknownFactory(); }
const helper = factory();
// ruleid: closure-context
sink(helper(source()));
