func test() {
 let value = "safe"
 guard let value = source() else { sink(value); return }
 // ruleid: flow
 sink(value)
}
