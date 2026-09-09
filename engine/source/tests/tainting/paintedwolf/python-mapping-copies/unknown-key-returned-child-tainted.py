def choose(mapping):
    return {**mapping}[unknown_key()]
value = choose({"value": {"safe": "fixed", "unsafe": source()}})
# ruleid: mapping-flow
sink(value["unsafe"])
