function tag(strings,value){
strings.push(value);
return strings;
}
// ruleid: flow
sink(tag(["fixed"],source()));
