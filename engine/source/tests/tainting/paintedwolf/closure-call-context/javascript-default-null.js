register(value => {
// ok: closure-context
 const helper = (input = value) => input; sink(helper(null));
});
