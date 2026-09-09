def consume(mapping):
    value = {"value": source(), **mapping}
    sink(value["value"])
if condition():
    mapping = {"value": "first"}
else:
    mapping = {"value": "second", "other": source()}
consume(mapping)
