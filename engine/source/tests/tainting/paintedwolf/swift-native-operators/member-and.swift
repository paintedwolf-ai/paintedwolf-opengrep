func source() -> Swift.String? { "input" }
func sink(_ value: Swift.String?) {}
struct Gate { static func && (lhs: Gate, rhs: @autoclosure () -> Swift.Bool) -> Swift.Bool { true } }
func test() {
 if Gate() && false {
  // ruleid: flow
  sink(source())
 }
}
