def test():
    values = {"bad": source(), "good": "safe"}
    copied = values
    # ruleid: flow
    sink(copied["bad"])
    # ok: flow
    sink(copied["good"])
