register(value => {
// ruleid: closure-context
 const clean = () => "safe"; const dirty = (a,b) => b; const helper = flag ? clean : dirty; sink(helper("safe", value));
});
