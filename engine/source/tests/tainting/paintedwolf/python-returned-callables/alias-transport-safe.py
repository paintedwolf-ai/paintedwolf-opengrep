def prepare(value):
    def consume():
        # ok: mapping-flow
        sink(value)
    alias = consume
    value = "safe"
    return alias
callback = prepare(source())
callback()
