type A = B; type B = u64;
fn f() {
sink(source().parse::<A>().unwrap());
}
