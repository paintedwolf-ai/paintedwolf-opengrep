use evil::*;
fn f() {
// ruleid: flow
sink(source().parse::<u64>().unwrap());
}
