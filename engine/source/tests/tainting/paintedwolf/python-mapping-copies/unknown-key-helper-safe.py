def consume(mapping):
    copied = {**mapping, "value": "safe"}
    # ok: mapping-flow
    sink(copied[unknown_key()])
consume({"value": source()})
