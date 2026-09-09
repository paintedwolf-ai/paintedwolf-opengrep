struct Flag {}
func && (lhs: Flag, rhs: @autoclosure () -> Bool) -> Bool { true }
func source() -> String { "input" }
func sink(_ value: String) {}
func example(flag: Flag) {
    // ruleid: flow
    if flag && false, true { sink(source()) }
}
