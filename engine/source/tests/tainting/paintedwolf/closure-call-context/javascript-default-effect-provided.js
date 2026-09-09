register(value => {
// ok: closure-context
 let out = "safe"; const fallback = () => {out = value; return false;}; const helper = (flag = fallback()) => "safe"; helper(true); sink(out);
});
