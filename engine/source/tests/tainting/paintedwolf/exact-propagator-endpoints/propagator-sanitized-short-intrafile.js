function test(){
let output=copy(clean(taint("abc")));sink(output);
}
