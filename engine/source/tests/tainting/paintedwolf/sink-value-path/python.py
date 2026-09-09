def queries(flag):
    # ruleid: flow
    sink([source(), "bound"])
    sink(["SELECT ?", source()])
    query = [source(), "bound"]
    # ruleid: flow
    sink(query)
    query = ["SELECT ?", source()]
    sink(query)
    query[0] = source()
    # ruleid: flow
    sink(query)
    query[0] = "SELECT ?"
    sink(query)
    query = [source(), "bound"]
    alias = query
    # ruleid: flow
    sink(alias)
    query = ["SELECT ?", source()]
    if flag:
        query = [source(), "bound"]
    # ruleid: flow
    sink(query)
    value = source()
    # ruleid: flow
    sink(value)
    sink([])
    sink(["fixed", [source()]])
    # ruleid: flow
    sink([[source()], "fixed"])
