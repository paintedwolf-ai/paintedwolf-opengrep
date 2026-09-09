def prepare(value):
    def consume():
        # ok: mapping-flow
        sink(value)
    try:
        return consume
    finally:
        value = "safe"
callback = prepare(source())
callback()
