func register(_ handler: (Swift.String) -> Swift.Void) { handler("input") }
func sink(_ value: Any) {}
func passthrough(_ value: Swift.String) -> Swift.String { value }

func test() {
 register { value in
  // ruleid: flow
  let identity = { (input: Swift.String) in input }; sink(identity(value))
 }
}
