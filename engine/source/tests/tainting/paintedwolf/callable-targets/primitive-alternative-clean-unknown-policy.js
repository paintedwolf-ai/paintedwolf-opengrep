register(value => {
// ok: closure-context
 const clean = a => "safe"; const helper = flag ? clean : "constant"; sink(helper(value));
});
