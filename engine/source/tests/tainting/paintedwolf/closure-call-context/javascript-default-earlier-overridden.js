register(value => {
// ok: closure-context
 const helper = (first, second = first) => second; sink(helper(value, "safe"));
});
