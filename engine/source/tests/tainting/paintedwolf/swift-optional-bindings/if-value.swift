func test() {
 if let value = source() {
  // ruleid: flow
  sink(value)
 }
}
