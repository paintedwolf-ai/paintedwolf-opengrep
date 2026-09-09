def copy(mapping):
    return {**mapping}
value = copy({"nested": {"tainted": source(), "safe": "safe"}})
# ruleid: mapping-flow
sink(value["nested"]["tainted"])
sink(value["nested"]["safe"])
