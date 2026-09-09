def test():
    values = source()
    selected = values
    # ruleid: flow
    sink(selected)
    values = "safe"
    safe = values
    # ok: flow
    sink(safe)
