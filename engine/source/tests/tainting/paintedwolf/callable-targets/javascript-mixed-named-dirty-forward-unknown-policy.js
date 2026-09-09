function outside() { return source(); }
register(value => {
const clean = () => "safe";
const helper = flag ? clean : outside;
// ruleid: closure-context
sink(helper());
});
