register(value => {
// ruleid: closure-context
 const clean = (a,b) => a; const dirty = (b,a) => a; const helper = flag ? clean : dirty; sink(helper("safe", value));
});
