func source() -> Swift.String? { "input" }
func sink(_ value: Swift.String?) {}
extension Swift.Bool { static func && (lhs: Swift.Bool, rhs: Swift.Bool) -> Swift.Bool { true } }
func test() {
 if false && false {
  // ruleid: flow
  sink(source())
 }
}
