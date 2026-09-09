func handler() {
 let value = source()
 let action = { (number: Int) in
 // ruleid: flow
 sink(value)
 }
 action(1)
}
