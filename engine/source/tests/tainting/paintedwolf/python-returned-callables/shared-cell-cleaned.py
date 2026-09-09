def prepare(value):
    def consume():
        # ok: mapping-flow
        sink(value)
    def replace():
        nonlocal value
        value = "safe"
    return consume, replace
callback, replace = prepare(source())
replace()
callback()
