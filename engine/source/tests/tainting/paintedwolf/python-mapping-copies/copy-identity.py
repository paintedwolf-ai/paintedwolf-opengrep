def copy(mapping):
    return {**mapping}
value = copy({"tainted": source(), "safe": "safe"})
# ruleid: mapping-flow
sink(value["tainted"])
sink(value["safe"])
