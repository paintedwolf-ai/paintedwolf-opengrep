register(value => {
// ruleid: closure-context
 const fallback = () => value; const helper = (input = fallback()) => input; sink(helper());
});
