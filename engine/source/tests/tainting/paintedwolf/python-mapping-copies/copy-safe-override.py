def copy(mapping):
    return {**mapping, "value": "safe"}
value = copy({"value": source(), "other": source()})
sink(value["value"])
# ruleid: mapping-flow
sink(value["other"])
