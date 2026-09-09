register(value => {
// ok: closure-context
 const helper = (enabled = false) => enabled ? value : "safe"; sink(helper());
});
