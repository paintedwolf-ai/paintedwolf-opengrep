func test() {
 let absent: String? = nil
 guard let value = absent else { return }
 sink(source())
}
