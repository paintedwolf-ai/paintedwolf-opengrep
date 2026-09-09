def consume(mapping):
    value = {**mapping, "value": "safe"}
    sink(value)
consume({"value": source()})
