func test() {
 let value = "safe"
 if let value = source() { sink("safe") }
 else { sink(value) }
}
