register(value => {
// ruleid: closure-context
 const clean = input => "safe"; const dirty = input => input; const helper = flag ? clean : dirty; sink(helper(value));
});
