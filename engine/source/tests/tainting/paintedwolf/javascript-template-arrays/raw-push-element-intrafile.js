function tag(strings,value){
strings.raw.push(value);
return strings.raw;
}
// ok: flow
sink(tag`fixed${source()}`);
