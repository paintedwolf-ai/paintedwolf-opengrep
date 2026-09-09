register(value => {
// ok: closure-context
 const helper = ({dirty, safe}) => safe; sink(helper({dirty:value, safe:"safe"}));
});
