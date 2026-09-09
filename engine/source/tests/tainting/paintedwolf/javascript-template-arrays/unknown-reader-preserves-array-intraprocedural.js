function tag(strings,value){
inspect(strings);
strings[0]=value;
return strings[0];
}
// ok: flow
sink(tag`fixed${source()}`);
