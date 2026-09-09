def consume(value):
    # ok: mapping-flow
    sink(value)
def prepare(consume):
    return consume
callback = prepare(lambda value: None)
callback(source())
