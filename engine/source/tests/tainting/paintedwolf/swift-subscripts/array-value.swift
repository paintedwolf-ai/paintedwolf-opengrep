func handler() {
let values = [source(), "safe"]
// ruleid: flow
sink(values[0])
sink(values[1])
}
