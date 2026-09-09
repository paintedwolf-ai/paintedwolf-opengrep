function factory() { if (flag) return unknownFactory(); return () => "safe"; }
const helper = factory();
// ok: closure-context
sink(helper(source()));
