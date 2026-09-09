func register(_ handler: (Swift.String) -> Swift.Void) { handler("input") }
func sink(_ value: Any) {}
func passthrough(_ value: Swift.String) -> Swift.String { value }

func test() {
 register { value in
  // ok: flow
  let discard = { (input: Swift.String) -> Swift.Void in passthrough(input) }; sink(discard(value))
 }
}
