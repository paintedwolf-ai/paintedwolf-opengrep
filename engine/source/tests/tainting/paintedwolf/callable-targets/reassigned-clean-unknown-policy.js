register(value => {
// ok: closure-context
 let helper = a => a; helper = a => "safe"; sink(helper(value));
});
