func test() {
 let value = source()
 let absent: String? = nil
 guard let value = absent else {
  // ruleid: flow
  sink(value)
  return
 }
 sink("safe")
}
