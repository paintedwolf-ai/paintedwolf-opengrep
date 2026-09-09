function tag(strings, value) {return value;}
// ruleid: flow
sink(tag`prefix${source()}suffix`);
