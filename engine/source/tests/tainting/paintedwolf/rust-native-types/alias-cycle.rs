type A = B; type B = A;
fn f() {
// ruleid: flow
sink(source().parse::<A>().unwrap());
}
