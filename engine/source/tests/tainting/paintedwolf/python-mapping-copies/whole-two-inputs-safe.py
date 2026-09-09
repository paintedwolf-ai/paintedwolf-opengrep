def consume(first, second):
    sink({**first, **second})
consume({"value": source()}, {"value": "safe"})
