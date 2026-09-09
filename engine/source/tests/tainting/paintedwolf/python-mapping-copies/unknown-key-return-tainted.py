def choose(mapping):
    return {**mapping, "value": "safe"}[unknown_key()]
value = choose({"value": source(), "other": source()})
# ruleid: mapping-flow
sink(value)
