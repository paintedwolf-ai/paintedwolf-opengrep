func handler() {
var values = ["key": "safe"]
values["key"] = source()
// ruleid: flow
sink(values["key"])
}
