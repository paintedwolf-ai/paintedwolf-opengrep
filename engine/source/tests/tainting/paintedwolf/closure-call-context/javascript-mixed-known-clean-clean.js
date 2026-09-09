register(value => {
// ok: closure-context
 const clean = input => "safe"; const other = input => "other"; const helper = flag ? clean : other; sink(helper(value));
});
