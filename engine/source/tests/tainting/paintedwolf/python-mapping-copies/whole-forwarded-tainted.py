def consume(mapping):
    # ruleid: mapping-flow
    sink({**mapping, "value": "safe"})
def forward(mapping):
    consume(mapping)
forward({"value": source(), "other": source()})
