def consume(mapping):
    value = {**mapping, "value": "safe"}
    # ruleid: mapping-flow
    sink(value)
consume({"value": source(), "other": source()})
