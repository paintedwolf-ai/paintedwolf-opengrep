func test() {
 let value = source()
 if let value {
  // ruleid: flow
  sink(value)
 }
}
