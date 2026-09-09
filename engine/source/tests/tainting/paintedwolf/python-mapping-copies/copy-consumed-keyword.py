def copy(value, **mapping):
    return {"value": source(), **mapping}
value = copy(value="safe", other="safe")
# ruleid: mapping-flow
sink(value["value"])
sink(value["other"])
