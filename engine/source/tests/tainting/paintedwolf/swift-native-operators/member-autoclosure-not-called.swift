struct Flag { static func && (lhs: Self, rhs: @autoclosure () -> Swift.Bool) -> Swift.Bool { true } }
func register(_ handler: (Swift.String) -> Void) { handler("input") }
func sink(_ value: Swift.String) -> Swift.Bool { false }
func test() {
 register { value in
  // ok: flow
  let _ = Flag() && sink(value)
 }
}
