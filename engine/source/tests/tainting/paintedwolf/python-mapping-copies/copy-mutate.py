def copy(mapping):
    value = {**mapping}
    value["safe"] = "safe"
    return value
original = {"tainted": source(), "safe": source()}
value = copy(original)
# ruleid: mapping-flow
sink(value["tainted"])
sink(value["safe"])
# ruleid: mapping-flow
sink(original["safe"])
