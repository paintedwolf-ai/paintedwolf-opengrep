function tag(strings,value){
strings[0]=value;
return strings[0];
}
// ok: flow
sink(tag`fixed${source()}`);
