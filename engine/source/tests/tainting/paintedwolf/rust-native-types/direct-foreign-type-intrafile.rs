
fn f() {
// ruleid: flow
sink(source().parse::<custom::u64>().unwrap());
}
