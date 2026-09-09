register(value => {
// ok: closure-context
 const helper = enabled => enabled ? value : "safe"; sink(helper(false));
});
