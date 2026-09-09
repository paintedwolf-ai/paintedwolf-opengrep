func test() {
 guard var value = source() else { return }
 value = "safe"
 sink(value)
}
