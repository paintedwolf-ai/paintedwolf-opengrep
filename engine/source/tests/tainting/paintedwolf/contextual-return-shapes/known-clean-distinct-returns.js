function factory() { if (flag) return value => "safe"; return () => "safe"; }
const helper = factory();
// ok: closure-context
sink(helper(source()));
