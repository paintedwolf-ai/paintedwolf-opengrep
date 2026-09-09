func handler() {
 let value = source()
 let action = { [value] in
 // ruleid: flow
 sink(value)
 }
 action()
}
