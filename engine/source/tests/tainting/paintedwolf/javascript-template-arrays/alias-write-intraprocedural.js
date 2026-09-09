function tag(strings,value){
const alias=strings;
alias[0]=value;
return strings[0];
}
// ok: flow
sink(tag`fixed${source()}`);
