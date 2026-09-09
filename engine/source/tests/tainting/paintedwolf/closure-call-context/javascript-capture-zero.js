register(value => {
// ruleid: closure-context
 const helper = () => value; sink(helper());
});
