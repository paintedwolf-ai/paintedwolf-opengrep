def literals():
    sink(b"fixed")
    sink(r"fixed\value")
    sink(br"fixed\value")
    # ruleid: flow
    sink(b"prefix" + source())
    # ruleid: flow
    sink(r"prefix" + source())
