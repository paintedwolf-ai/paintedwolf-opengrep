func source() -> Swift.String? { "input" }
func sourceFlag() -> Swift.Bool? { true }
func flag() -> Swift.Bool { Swift.Bool.random() }
func sink(_ value: Swift.String?) {}
func test() {
 if false && flag() == false || true {
  // ruleid: flow
  sink(source())
 }
}
