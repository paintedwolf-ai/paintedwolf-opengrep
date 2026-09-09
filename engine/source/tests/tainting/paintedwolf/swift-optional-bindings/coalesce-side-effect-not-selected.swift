func test() {
 let value: String? = "safe"
 let result = value ?? touched(source())
 sink(result)
}
