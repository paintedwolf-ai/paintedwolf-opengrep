register(value => {
// ruleid: closure-context
 const helper = (...args) => value; sink(helper("safe", "more"));
});
