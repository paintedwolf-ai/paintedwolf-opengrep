func test() {
 if let first = source(), let second = first as String? {
  // ruleid: flow
  sink(second)
 }
}
