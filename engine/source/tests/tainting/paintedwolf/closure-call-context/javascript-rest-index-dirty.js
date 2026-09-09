register(value => {
// ruleid: closure-context
 const helper = (...args) => args[1]; sink(helper("safe", value));
});
