register(value => {
// ok: closure-context
 let out = value; const helper = ignored => {out = "safe";}; helper("safe"); sink(out);
});
