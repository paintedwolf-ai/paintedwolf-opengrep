function tag(strings,value){
strings=[value];
return strings[0];
}
// ruleid: flow
sink(tag`fixed${source()}`);
