func test() {
 if let first = source() {
  let second: String? = first
  if let second {
   // ruleid: flow
   sink(second)
  }
 }
}
