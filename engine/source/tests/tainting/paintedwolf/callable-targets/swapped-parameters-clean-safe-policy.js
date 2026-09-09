register(value => {
// ok: closure-context
 const clean = (a,b) => a; const other = (b,a) => b; const helper = flag ? clean : other; sink(helper("safe", value));
});
