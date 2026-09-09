func handler() {
let key = source()
let values = ["one": "safe"]
sink(values[key] ?? "fallback")
}
