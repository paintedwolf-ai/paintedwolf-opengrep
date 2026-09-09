function factory() { if (flag) return () => "safe"; throw "stop"; }
const helper = factory();
// ok: closure-context
sink(helper(source()));
