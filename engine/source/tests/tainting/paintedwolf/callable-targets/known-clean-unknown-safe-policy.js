register(value => {
// ok: closure-context
 const clean = a => "safe"; const helper = flag ? clean : unknownFactory(); sink(helper(value));
});
