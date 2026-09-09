def prepare(mapping):
    def consume():
        # ruleid: mapping-flow
        sink({**mapping, "value": "safe"})
    return consume
callback = prepare({"value": source(), "other": source()})
callback()
