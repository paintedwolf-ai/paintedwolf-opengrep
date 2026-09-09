func source() -> String { "input" }
func sink(_ value: String) {}
func example(flag: Bool) {
    // ok: flow
    if flag, false { sink(source()) }
}
