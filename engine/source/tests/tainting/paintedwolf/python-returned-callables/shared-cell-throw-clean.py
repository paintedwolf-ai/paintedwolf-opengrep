def prepare(value):
    def consume():
        # ok: mapping-flow
        sink(value)
    def replace():
        nonlocal value
        value = "safe"
        raise ValueError("done")
    return consume, replace
callback, replace = prepare(source())
try:
    replace()
except ValueError:
    pass
callback()
