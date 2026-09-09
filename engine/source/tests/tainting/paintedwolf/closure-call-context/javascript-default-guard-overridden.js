register(value => {
// ok: closure-context
 const helper = (enabled = true) => enabled ? value : "safe"; sink(helper(false));
});
