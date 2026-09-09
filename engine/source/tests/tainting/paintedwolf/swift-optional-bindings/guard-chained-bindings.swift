func test() {
 guard let first = source(), let second = first as String? else { return }
 // ruleid: flow
 sink(second)
}
