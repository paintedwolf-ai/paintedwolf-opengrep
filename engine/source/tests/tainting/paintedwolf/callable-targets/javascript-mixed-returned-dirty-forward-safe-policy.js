function factory() { return () => source(); }
register(value => {
const clean = () => "safe";
const helper = flag ? clean : factory();
// ruleid: closure-context
sink(helper());
});
