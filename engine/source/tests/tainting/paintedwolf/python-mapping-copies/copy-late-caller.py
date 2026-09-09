def copy(mapping):
    return {"value": source(), **mapping}
value = copy({"value": "safe", "other": source()})
sink(value["value"])
# ruleid: mapping-flow
sink(value["other"])
