function factory() { return () => "safe"; }
register(value => {
const clean = () => "safe";
const helper = flag ? clean : factory();
// ok: closure-context
sink(helper());
});
