func test() {
 let value: String? = "safe"
 sink(value ?? source())
}
