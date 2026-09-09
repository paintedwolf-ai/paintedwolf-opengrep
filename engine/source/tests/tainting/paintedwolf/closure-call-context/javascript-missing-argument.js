register(value => {
// ok: closure-context
 const helper = input => input; sink(helper());
});
