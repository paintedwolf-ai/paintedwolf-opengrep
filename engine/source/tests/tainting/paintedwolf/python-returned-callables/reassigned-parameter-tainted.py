def prepare(value):
    def consume():
        # ruleid: mapping-flow
        sink(value)
    value = source()
    return consume
callback = prepare("safe")
callback()
