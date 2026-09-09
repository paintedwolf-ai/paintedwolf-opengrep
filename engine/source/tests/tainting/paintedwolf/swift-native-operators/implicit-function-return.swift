func register(_ handler: (Swift.String) -> Swift.Void) { handler("input") }
func sink(_ value: Any) {}
func passthrough(_ value: Swift.String) -> Swift.String { value }
func identity(_ value: Swift.String) -> Swift.String { value }
func test() {
 register { value in
  // ruleid: flow
  sink(identity(value))
 }
}
