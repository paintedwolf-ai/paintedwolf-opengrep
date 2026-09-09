func test() {
 let absent: String? = nil
 if let first = absent, let second = source() { sink(second) }
}
