function outside() { return source(); }
register(value => {
const clean = () => "safe";
const helper = flag ? outside : clean;
// ruleid: closure-context
sink(helper());
});
