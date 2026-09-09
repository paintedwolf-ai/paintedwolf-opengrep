function tag(strings,value){
strings.push(value);
return strings;
}
// ok: flow
sink(tag`fixed${source()}`);
