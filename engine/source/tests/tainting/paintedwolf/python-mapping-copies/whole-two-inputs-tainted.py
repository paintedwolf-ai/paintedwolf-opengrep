def consume(first, second):
    # ruleid: mapping-flow
    sink({**first, **second})
consume({"value": source(), "other": source()}, {"value": "safe"})
