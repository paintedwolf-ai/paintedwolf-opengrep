func test() {
 guard let value = source() else { return }
 // ruleid: flow
 sink(value)
}
