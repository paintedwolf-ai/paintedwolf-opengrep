function outside() { return "safe"; }
register(value => {
const clean = () => "safe";
const helper = flag ? clean : outside;
// ok: closure-context
sink(helper());
});
