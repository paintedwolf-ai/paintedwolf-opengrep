func test() {
 let value = source()
 let absent: String? = nil
 if let value = absent { sink("safe") }
 else {
  // ruleid: flow
  sink(value)
 }
}
