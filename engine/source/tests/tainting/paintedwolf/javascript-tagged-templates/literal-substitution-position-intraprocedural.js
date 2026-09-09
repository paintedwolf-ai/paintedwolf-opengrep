function tag(strings, first, second) {return second;}
// ok: flow
sink(tag`${source()}${"fixed"}`);
