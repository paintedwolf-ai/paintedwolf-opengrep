def prepare(mapping):
    def consume():
        sink({**mapping, "value": "safe"})
    return consume
callback = prepare({"value": source()})
callback()
