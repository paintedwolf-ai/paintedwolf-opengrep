function tag(strings,value){
delete strings[0];
return strings[0];
}
// ok: flow
sink(tag`fixed${source()}`);
