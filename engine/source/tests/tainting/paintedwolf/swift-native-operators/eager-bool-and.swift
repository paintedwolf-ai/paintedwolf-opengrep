func source() -> Swift.String? { "input" }
func sourceFlag() -> Swift.Bool? { true }
func flag() -> Swift.Bool { Swift.Bool.random() }
func sink(_ value: Swift.String?) {}
func && (lhs: Swift.Bool, rhs: Swift.Bool) -> Swift.Bool { true }
func test() {
 if false && false {
 // ruleid: flow
 sink(source())
 }
}
