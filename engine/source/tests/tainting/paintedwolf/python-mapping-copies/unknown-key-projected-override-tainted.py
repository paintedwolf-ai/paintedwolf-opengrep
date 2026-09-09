def choose(mapping):
    chosen = {**mapping}[unknown_key()]
    chosen["value"] = "safe"
    # ruleid: mapping-flow
    sink(chosen)
choose({"value": {"value": source(), "other": source()}})
