function outside() { return "safe"; }
register(value => {
const clean = () => "safe";
const helper = flag ? outside : clean;
// ok: closure-context
sink(helper());
});
