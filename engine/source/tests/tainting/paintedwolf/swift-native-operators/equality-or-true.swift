func source() -> Swift.String? { "input" }
func sourceFlag() -> Swift.Bool? { true }
func flag() -> Swift.Bool { Swift.Bool.random() }
func sink(_ value: Swift.String?) {}
func test() {
 if source() != nil || true {
  // ruleid: flow
  sink(source())
 }
}
