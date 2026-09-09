def choose(mapping):
    chosen = {**mapping}[unknown_key()]
    chosen["value"] = "safe"
    # ok: mapping-flow
    sink(chosen)
choose({"value": {"value": source()}})
