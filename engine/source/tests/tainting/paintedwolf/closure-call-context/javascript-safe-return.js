register(value => {
// ok: closure-context
 const helper = (...args) => "safe"; sink(helper(value));
});
