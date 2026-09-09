fn f() { make_alias!();
// ruleid: flow
sink(source().parse::<u64>().unwrap());
}
