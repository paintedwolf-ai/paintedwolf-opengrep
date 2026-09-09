func handler() {
var values = ["key": source()]
values["key"] = "safe"
sink(values["key"])
}
