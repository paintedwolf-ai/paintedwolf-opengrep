def copy(mapping):
    return {**mapping, "safe": "safe"}
def forward(mapping):
    return copy(mapping)
value = forward({"tainted": source(), "safe": source()})
# ruleid: mapping-flow
sink(value["tainted"])
sink(value["safe"])
