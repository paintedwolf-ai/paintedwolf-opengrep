function tag(strings, first, second) {return first;}
let value="fixed";
// ok: flow
sink(tag`${value}${value=source()}`);
