def prepare(value):
    def consume():
        # ruleid: mapping-flow
        sink(value)
    return consume
callback = prepare(source())
callback()
