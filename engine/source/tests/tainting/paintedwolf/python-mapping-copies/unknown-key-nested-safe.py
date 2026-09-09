def choose(mapping):
    return {**mapping}[unknown_key()]["safe"]
value = choose({"value": {"safe": "fixed", "unsafe": source()}})
# ok: mapping-flow
sink(value)
