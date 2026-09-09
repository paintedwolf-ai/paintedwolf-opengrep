register(value => {
// ruleid: closure-context
 const helper = enabled => enabled ? value : "safe"; sink(helper(true));
});
