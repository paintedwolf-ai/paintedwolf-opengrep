fn f() {
// ruleid: flow
sink(source().to_owned().parse::<u64>().unwrap()); }
