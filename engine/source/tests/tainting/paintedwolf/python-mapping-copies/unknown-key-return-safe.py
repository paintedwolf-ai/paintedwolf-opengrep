def choose(mapping):
    return {**mapping, "value": "safe"}[unknown_key()]
value = choose({"value": source()})
# ok: mapping-flow
sink(value)
