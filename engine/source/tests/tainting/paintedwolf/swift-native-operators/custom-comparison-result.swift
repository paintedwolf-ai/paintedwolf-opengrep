func source() -> Swift.String? { "input" }
func sourceFlag() -> Swift.Bool? { true }
func flag() -> Swift.Bool { Swift.Bool.random() }
func sink(_ value: Swift.String?) {}
struct Token {}
struct Gate {}
func == (lhs: Token, rhs: Token) -> Gate { Gate() }
func && (lhs: Gate, rhs: @autoclosure () -> Swift.Bool) -> Swift.Bool { true }
func test() {
 if (Token() == Token()) && false {
 // ruleid: flow
 sink(source())
 }
}
