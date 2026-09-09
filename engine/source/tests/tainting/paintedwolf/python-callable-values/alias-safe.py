def consume(value):
    # ok: mapping-flow
    sink(value)
callback = consume
callback("safe")
