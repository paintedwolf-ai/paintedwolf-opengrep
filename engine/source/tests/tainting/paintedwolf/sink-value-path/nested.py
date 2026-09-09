def queries():
    # ruleid: flow
    sink(["fixed", [source(), "bound"]])
    sink([source(), ["SELECT ?", source()]])
    data = [source(), ["SELECT ?", source()]]
    sink(data)
    data[1][0] = source()
    # ruleid: flow
    sink(data)
    data[1][0] = "fixed"
    sink(data)
