register(value => {
// ruleid: closure-context
 const helper = ignored => value; sink(helper("safe"));
});
