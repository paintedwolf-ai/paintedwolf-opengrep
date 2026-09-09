register(value => {
// ruleid: closure-context
 const out = {field:"safe"}; const helper = target => {target.field = value;}; helper(out); sink(out.field);
});
