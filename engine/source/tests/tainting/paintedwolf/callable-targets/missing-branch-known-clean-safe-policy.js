register(value => {
// ok: closure-context
 let helper = external; if(flag) helper = a => "safe"; sink(helper(value));
});
