def consume(mapping):
    value = {"value": "safe", **mapping}
    # ruleid: mapping-flow
    sink(value["value"])
consume({"value": source()})
