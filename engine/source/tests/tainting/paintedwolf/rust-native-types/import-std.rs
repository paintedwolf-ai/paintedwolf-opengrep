use std::primitive::u64 as Count;
fn f() {
sink(source().parse::<Count>().unwrap());
}
