register(value => {
// ruleid: closure-context
 const helper = ({dirty, safe}) => dirty; sink(helper({dirty:value, safe:"safe"}));
});
