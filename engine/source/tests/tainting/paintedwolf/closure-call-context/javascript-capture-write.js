register(value => {
// ruleid: closure-context
 let out = "safe"; const helper = ignored => {out = value;}; helper("safe"); sink(out);
});
