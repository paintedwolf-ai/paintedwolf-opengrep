def prepare(value):
    def consume():
        # ok: mapping-flow
        sink(value)
    value = "safe"
    return consume
callback = prepare(source())
callback()
