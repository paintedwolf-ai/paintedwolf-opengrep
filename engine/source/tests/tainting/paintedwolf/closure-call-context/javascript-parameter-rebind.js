register(value => {
// ruleid: closure-context
 const out = {field:value}; const helper = target => {target = {field:"safe"};}; helper(out); sink(out.field);
});
