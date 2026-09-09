func test() {
 let value = source()
 guard let value else { return }
 // ruleid: flow
 sink(value)
}
