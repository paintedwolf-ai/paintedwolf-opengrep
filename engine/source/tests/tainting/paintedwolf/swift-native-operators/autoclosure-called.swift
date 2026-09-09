struct Flag {}
func register(_ handler: (Swift.String) -> Void) { handler("input") }
func sink(_ value: Swift.String) -> Swift.Bool { false }
func && (lhs: Flag, rhs: @autoclosure () -> Swift.Bool) -> Swift.Bool { rhs() }
func test() {
 register { value in
  // ruleid: flow
  let _ = Flag() && sink(value)
 }
}
