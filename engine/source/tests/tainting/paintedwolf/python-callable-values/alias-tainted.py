def consume(value):
    # ruleid: mapping-flow
    sink(value)
callback = consume
callback(source())
