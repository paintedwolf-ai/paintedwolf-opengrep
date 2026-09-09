def consume(mapping):
    copied = {**mapping, "value": "safe"}
    # ruleid: mapping-flow
    sink(copied[unknown_key()])
consume({"value": source(), "other": source()})
