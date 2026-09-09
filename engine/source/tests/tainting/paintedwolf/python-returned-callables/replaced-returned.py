def prepare(value):
    def consume():
        # ok: mapping-flow
        sink(value)
    consume = lambda: None
    return consume
callback = prepare(source())
callback()
