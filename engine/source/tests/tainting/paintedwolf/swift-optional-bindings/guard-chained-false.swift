func test() {
 guard let value = source(), false else { return }
 sink(value)
}
