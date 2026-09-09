register(value => {
// ok: closure-context
 const clean = () => "safe"; const other = (a,b) => a; const helper = flag ? clean : other; sink(helper("safe", value));
});
