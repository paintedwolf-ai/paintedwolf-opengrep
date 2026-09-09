def consume(mapping):
    value = {"value": source(), **mapping}
    # ruleid: mapping-flow
    sink(value["value"])
consume({"other": "safe"})
