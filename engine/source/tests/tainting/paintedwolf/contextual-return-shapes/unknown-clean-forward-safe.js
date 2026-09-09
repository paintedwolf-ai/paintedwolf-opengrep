function factory() { if (flag) return () => "safe"; return unknownFactory(); }
const helper = factory();
// ok: closure-context
sink(helper(source()));
