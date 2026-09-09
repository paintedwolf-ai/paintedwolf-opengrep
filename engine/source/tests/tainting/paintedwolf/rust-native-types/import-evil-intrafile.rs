use evil::u64 as Count;
fn f() {
// ruleid: flow
sink(source().parse::<Count>().unwrap());
}
