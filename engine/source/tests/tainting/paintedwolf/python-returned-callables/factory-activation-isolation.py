def prepare(value):
    def consume():
        # ruleid: mapping-flow
        sink(value)
    return consume
dangerous = prepare(source())
clean = prepare("safe")
clean()
dangerous()
