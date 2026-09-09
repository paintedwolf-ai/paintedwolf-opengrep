func handler() {
 let value = source()
 let action = {
 // ruleid: flow
 sink(value)
 }
 action()
}
