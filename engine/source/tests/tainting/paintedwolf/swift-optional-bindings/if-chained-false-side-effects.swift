func test() {
 // ruleid: flow
 if let value = sinkReturning(source()), false { sink(value) }
}
