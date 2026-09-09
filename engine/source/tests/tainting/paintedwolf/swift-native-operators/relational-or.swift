func source() -> Swift.String? { "input" }
func sourceFlag() -> Swift.Bool? { true }
func flag() -> Swift.Bool { Swift.Bool.random() }
func sink(_ value: Swift.String?) {}
func test() {
 if 3 < 2 || 1 >= 2 {
  sink(source())
 }
}
