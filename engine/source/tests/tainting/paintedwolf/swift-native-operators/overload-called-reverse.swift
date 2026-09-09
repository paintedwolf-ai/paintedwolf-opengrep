struct Called {}
struct Ignored {}
func register(_ handler: (Swift.String) -> Void) { handler("input") }
func sink(_ value: Swift.String) -> Swift.Bool { false }
func && (lhs: Ignored, rhs: @autoclosure () -> Swift.Bool) -> Swift.Bool { true }
func && (lhs: Called, rhs: @autoclosure () -> Swift.Bool) -> Swift.Bool { rhs() }
func test() {
 register { value in
  // ruleid: flow
  let _ = Called() && sink(value)
 }
}
