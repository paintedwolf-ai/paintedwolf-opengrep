register(value => {
// ok: closure-context
 const helper = (...args) => args[0]; sink(helper("safe", value));
});
