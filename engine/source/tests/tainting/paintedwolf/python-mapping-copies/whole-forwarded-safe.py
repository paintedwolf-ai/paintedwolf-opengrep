def consume(mapping):
    sink({**mapping, "value": "safe"})
def forward(mapping):
    consume(mapping)
forward({"value": source()})
