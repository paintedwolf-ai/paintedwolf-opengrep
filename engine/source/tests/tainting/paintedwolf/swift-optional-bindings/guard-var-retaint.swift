func test() {
 let input: String? = "safe"
 guard var value = input else { return }
 value = source() ?? "safe"
 // ruleid: flow
 sink(value)
}
