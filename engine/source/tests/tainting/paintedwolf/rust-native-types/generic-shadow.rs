fn f<u64>() {
// ruleid: flow
sink(source().parse::<u64>().unwrap());
}
