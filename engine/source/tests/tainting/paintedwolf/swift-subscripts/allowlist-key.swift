func handler() {
let key = source()
let values = ["one": "safe", "two": "constant"]
sink(values[key])
}
