func request(_ input: Swift.String) -> Swift.String { input }
func sink(_ value: Swift.String) {}
func test() {
 // ruleid: flow
 sink(request("safe"))
}
