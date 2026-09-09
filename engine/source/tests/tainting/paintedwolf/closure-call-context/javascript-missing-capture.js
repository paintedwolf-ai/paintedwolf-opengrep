register(value => {
// ruleid: closure-context
 const helper = (a, b) => value; sink(helper("safe"));
});
