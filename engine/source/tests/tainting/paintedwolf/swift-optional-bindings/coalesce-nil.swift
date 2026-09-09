func test() {
 let value: String? = nil
 // ruleid: flow
 sink(value ?? source())
}
