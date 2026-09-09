fields = {"value": source()}
copy = {**fields, "value": "safe"}
# ok: mapping-flow
sink(copy[unknown_key()])
