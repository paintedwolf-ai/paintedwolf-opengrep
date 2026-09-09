func handler() {
 let action = { [value = source()] in
 sink(value)
 }
 action()
}
