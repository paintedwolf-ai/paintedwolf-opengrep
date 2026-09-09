register(value => {
// ruleid: closure-context
 const helper = (input = value) => input; sink(helper(undefined));
});
