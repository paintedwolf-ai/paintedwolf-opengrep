function test(){
let output=copy((clean(taint("aaa"))));
sink(output);
}
