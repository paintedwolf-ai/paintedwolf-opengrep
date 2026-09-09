fn f() {
// ruleid: flow
sink(source().parse::<u64>().unwrap());
}
type u64 = String;
