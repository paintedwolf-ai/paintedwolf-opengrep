func handler() {
let values = ["key": source()]
// ruleid: flow
sink(flag ? values["key"] : "safe")
}
