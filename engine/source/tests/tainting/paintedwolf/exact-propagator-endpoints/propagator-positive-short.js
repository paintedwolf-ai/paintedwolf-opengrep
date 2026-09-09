function test(){
let output=copy(taint("aaa"));
// ruleid: flow
sink(output);
}
