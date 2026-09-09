def handler() {
 def value = source()
 def read = { -> value }
 // ruleid: flow
 sink(read())
}
