register(value => {
// ruleid: closure-context
 const helper = ignored => value; const alias = helper; sink(alias("safe"));
});
