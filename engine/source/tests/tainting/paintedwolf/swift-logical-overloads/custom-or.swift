struct Flag {}
func || (lhs: Flag, rhs: @autoclosure () -> Bool) -> Bool { false }
func source() -> String { "input" }
func sink(_ value: String) {}
func example(flag: Flag) {
    // ruleid: flow
    if flag || true {} else { sink(source()) }
}
