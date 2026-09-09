register(value => {
// ok: closure-context
 const fallback = () => value; const helper = (input = fallback()) => input; sink(helper("safe"));
});
