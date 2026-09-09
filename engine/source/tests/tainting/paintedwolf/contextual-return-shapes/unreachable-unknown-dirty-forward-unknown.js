function factory() { if (false) return unknownFactory(); return () => source(); }
const helper = factory();
// ruleid: closure-context
sink(helper(source()));
