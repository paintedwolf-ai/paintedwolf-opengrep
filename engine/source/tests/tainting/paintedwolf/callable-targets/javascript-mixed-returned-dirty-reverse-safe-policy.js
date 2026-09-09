function factory() { return () => source(); }
register(value => {
const clean = () => "safe";
const helper = flag ? factory() : clean;
// ruleid: closure-context
sink(helper());
});
