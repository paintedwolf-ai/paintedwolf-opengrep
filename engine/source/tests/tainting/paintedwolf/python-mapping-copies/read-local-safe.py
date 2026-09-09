def consume(mapping):
    value = {"value": source(), **mapping}
    sink(value["value"])
value = {"value": "safe"}
consume(value)
