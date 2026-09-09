function tag(strings,value){
strings[0]=value;
return strings[0];
}
// ruleid: flow
sink(tag(["fixed"],source()));
