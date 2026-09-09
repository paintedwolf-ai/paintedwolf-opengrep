func source() -> Swift.String? { "input" }
func sourceFlag() -> Swift.Bool? { true }
func flag() -> Swift.Bool { Swift.Bool.random() }
func sink(_ value: Swift.String?) {}
infix operator <~>: ComparisonPrecedence
func <~> (lhs: Swift.Bool, rhs: Swift.Bool) -> Swift.Bool { lhs != rhs }
func test() {
 if (flag() <~> false) == false && false {
  sink(source())
 }
}
