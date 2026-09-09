register(value => {
// ruleid: closure-context
 let helper = ignored => "safe"; helper = ignored => value; sink(helper("safe"));
});
