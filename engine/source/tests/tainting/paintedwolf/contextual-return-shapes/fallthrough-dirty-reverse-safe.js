function factory() { if (!flag) return () => source(); }
const helper = factory();
// ruleid: closure-context
sink(helper(source()));
