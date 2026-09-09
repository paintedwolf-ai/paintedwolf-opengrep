function tag(strings, value) {return strings.raw[0];}
// ok: flow
sink(tag`fixed\n${source()}`);
