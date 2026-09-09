def copy(mapping):
    for item in values():
        mapping = {**mapping, "safe": "safe"}
    return mapping
value = copy({"tainted": source(), "safe": "safe"})
# ruleid: mapping-flow
sink(value["tainted"])
sink(value["safe"])
