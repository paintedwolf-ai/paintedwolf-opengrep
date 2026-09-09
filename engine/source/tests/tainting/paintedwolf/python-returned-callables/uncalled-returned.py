def prepare(value):
    def consume():
        # ok: mapping-flow
        sink(value)
    return consume
callback = prepare(source())
