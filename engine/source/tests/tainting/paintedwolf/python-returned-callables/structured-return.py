def prepare(value):
    def consume():
        # ruleid: mapping-flow
        sink(value)
    return {"callback": consume}
callbacks = prepare(source())
callbacks["callback"]()
