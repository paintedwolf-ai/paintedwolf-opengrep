func source() -> Swift.String? { "input" }
func sourceFlag() -> Swift.Bool? { true }
func flag() -> Swift.Bool { Swift.Bool.random() }
func sink(_ value: Swift.String?) {}
struct Flag {}
func && (lhs: Swift.Bool, rhs: @autoclosure () -> Flag) -> Swift.Bool { true }
func test() {
 if false && Flag() {
 // ruleid: flow
 sink(source())
 }
}
