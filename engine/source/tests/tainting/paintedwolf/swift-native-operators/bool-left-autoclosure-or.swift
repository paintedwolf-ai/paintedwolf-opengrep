func source() -> Swift.String? { "input" }
func sourceFlag() -> Swift.Bool? { true }
func flag() -> Swift.Bool { Swift.Bool.random() }
func sink(_ value: Swift.String?) {}
struct Flag {}
func || (lhs: Swift.Bool, rhs: @autoclosure () -> Flag) -> Swift.Bool { false }
func test() {
 if true || Flag() {} else {
 // ruleid: flow
 sink(source())
 }
}
