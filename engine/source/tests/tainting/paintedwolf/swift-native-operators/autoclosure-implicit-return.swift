func register(_ handler: (Swift.String) -> Swift.Void) { handler("input") }
func sink(_ value: Any) {}
func passthrough(_ value: Swift.String) -> Swift.String { value }
struct Flag {}
func && (lhs: Flag, rhs: @autoclosure () -> Swift.String) -> Swift.String { rhs() }
func test() {
 register { value in
  // ruleid: flow
  sink(Flag() && value)
 }
}
