register(value => {
// ok: closure-context
 const helper = () => "safe"; sink(helper(value));
});
