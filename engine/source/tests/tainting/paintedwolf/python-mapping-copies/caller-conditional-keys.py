def consume(mapping):
    value = {"value": source(), **mapping}
    # ruleid: mapping-flow
    sink(value["value"])
if condition():
    mapping = {"value": "safe"}
else:
    mapping = {"other": "safe"}
consume(mapping)
