func source() -> Swift.String? { "input" }
func sourceFlag() -> Swift.Bool? { true }
func flag() -> Swift.Bool { Swift.Bool.random() }
func sink(_ value: Swift.String?) {}
typealias Decision = Swift.Bool
func decide() -> Decision { flag() }
func test() {
 if decide() && false { sink(source()) }
}
