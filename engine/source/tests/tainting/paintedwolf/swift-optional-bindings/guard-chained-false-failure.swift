func test() {
 guard let value = source(), false else {
  // ruleid: flow
  sink(source())
  return
 }
 sink(value)
}
