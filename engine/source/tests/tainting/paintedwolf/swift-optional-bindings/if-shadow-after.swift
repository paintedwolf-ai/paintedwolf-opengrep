func test() {
 let value = "safe"
 if let value = source() {
  // ruleid: flow
  sink(value)
 }
 sink(value)
}
