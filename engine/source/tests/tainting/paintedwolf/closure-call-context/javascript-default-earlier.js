register(value => {
// ruleid: closure-context
 const helper = (first, second = first) => second; sink(helper(value));
});
