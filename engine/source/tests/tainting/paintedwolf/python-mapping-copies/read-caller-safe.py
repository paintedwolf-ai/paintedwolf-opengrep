def consume(mapping):
    value = {**mapping, "value": "safe"}
    sink(value["value"])
consume({"value": source()})
