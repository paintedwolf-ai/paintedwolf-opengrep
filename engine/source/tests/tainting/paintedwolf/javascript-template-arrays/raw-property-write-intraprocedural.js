function tag(strings,value){
strings.raw=[value];
return strings.raw[0];
}
// ok: flow
sink(tag`fixed${source()}`);
