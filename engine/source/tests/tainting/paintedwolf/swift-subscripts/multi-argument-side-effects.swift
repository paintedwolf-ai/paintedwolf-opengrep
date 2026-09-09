func example() {
    let table = ["safe": "value"]
    let result = table[
        // ruleid: flow
        sink(source()),
        // ruleid: flow
        default: sink(source())
    ]
}
