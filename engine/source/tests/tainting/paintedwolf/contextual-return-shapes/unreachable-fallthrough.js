function factory() { if (true) return () => "safe"; }
const helper = factory();
// ok: closure-context
sink(helper(source()));
