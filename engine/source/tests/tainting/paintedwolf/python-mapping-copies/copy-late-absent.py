def copy(mapping):
    return {"value": source(), **mapping}
value = copy({"other": "safe"})
# ruleid: mapping-flow
sink(value["value"])
sink(value["other"])
