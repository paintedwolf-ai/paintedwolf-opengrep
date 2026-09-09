def consume(mapping):
    value = {"value": source(), **mapping}
    sink(value["value"])
consume({"value": "safe"})
