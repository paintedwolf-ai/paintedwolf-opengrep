def choose(mapping):
    return {**mapping}[unknown_key()]
value = choose({"value": {"safe": "fixed", "unsafe": source()}})
# ok: mapping-flow
sink(value["safe"])
