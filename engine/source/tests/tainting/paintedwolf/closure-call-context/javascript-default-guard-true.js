register(value => {
// ruleid: closure-context
 const helper = (enabled = true) => enabled ? value : "safe"; sink(helper());
});
