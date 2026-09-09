function factory() { return () => "safe"; }
register(value => {
const clean = () => "safe";
const helper = flag ? factory() : clean;
// ok: closure-context
sink(helper());
});
