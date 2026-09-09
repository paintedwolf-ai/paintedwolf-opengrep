def prepare():
    def consume(value):
        # ruleid: mapping-flow
        sink(value)
    return consume
callback = prepare()
callback(source())
