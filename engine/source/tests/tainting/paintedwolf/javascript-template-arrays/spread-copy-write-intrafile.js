function tag(strings,value){
const copy=[...strings];
copy[0]=value;
return copy[0];
}
// ruleid: flow
sink(tag`fixed${source()}`);
