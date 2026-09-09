func source() -> Swift.String? { "input" }
func sink(_ value: Swift.String?) {}
struct Gate {}
extension Gate { static func && (lhs: Self, rhs: @autoclosure () -> Swift.Bool) -> Swift.Bool { true } }
func test() {
 if Gate() && false {
  // ruleid: flow
  sink(source())
 }
}
