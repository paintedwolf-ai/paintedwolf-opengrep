def consume(mapping):
    value = {"value": source(), **mapping}
    sink(value["value"])
def forward(mapping):
    consume(mapping)
forward({"value": "safe"})
