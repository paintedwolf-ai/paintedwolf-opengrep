extern crate evil as core; use core::primitive::u64 as Count;
fn f() {
// ruleid: flow
sink(source().parse::<Count>().unwrap());
}
