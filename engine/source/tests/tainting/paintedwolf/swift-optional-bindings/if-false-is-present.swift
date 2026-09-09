func test() {
 let flag: Bool? = false
 if let value = flag {
  // ruleid: flow
  sink(source())
 }
}
