func register(_ handler: (Swift.String) -> Swift.Void) { handler("input") }
func sink(_ value: Any) {}
func passthrough(_ value: Swift.String) -> Swift.String { value }
func discard(_ value: Swift.String) -> Swift.Void { passthrough(value) }
func test() {
 register { value in
  // ok: flow
  sink(discard(value))
 }
}
