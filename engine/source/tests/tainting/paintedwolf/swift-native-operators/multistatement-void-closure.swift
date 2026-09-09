func register(_ handler: (Swift.String) -> Swift.Void) { handler("input") }
func sink(_ value: Any) {}
func passthrough(_ value: Swift.String) -> Swift.String { value }
func test() {
 register { value in
  let discard = { (input: Swift.String) -> Swift.Void in
   let copy = input
   passthrough(copy)
  }
  // ok: flow
  sink(discard(value))
 }
}
