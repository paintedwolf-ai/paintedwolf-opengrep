func test() {
 let input: Bool? = false
 guard let value = input else { return }
 // ruleid: flow
 sink(source())
}
