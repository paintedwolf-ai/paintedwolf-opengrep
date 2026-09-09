def copy(mapping, flag):
    if flag:
        value = {**mapping, "safe": "safe"}
    else:
        value = {"safe": "safe", **mapping}
    return value
value = copy({"value": source(), "safe": "safe"}, condition())
# ruleid: mapping-flow
sink(value["value"])
sink(value["safe"])
