def consume(value, **mapping):
    copied = {"value": source(), **mapping}
    # ruleid: mapping-flow
    sink(copied["value"])
consume(value="safe", other="safe")
