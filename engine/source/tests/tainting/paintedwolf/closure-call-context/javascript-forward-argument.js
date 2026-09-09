register(value => {
// ruleid: closure-context
 const helper = input => input; sink(helper(value));
});
