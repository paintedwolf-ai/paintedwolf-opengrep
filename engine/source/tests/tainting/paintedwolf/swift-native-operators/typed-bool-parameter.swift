func source() -> Swift.String? { "input" }
func sourceFlag() -> Swift.Bool? { true }
func flag() -> Swift.Bool { Swift.Bool.random() }
func sink(_ value: Swift.String?) {}

func test() {
 func inner(_ decision: Swift.Bool) { if decision && false { sink(source()) } }
 inner(flag())
}
