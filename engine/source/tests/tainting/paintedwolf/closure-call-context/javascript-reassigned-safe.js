register(value => {
// ok: closure-context
 let helper = ignored => value; helper = ignored => "safe"; sink(helper("safe"));
});
