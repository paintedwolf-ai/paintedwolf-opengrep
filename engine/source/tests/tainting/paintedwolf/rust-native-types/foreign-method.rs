
fn f() {
// ruleid: flow
sink(opaque(source()).parse::<u64>().unwrap());
}
