function tag(strings, value) {return strings[0];}
// ok: flow
sink(tag`${source()}`);
