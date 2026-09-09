func test() {
 let value: String? = "safe"
 if var value {
  value = source() ?? "safe"
  // ruleid: flow
  sink(value)
 }
 sink(value)
}
