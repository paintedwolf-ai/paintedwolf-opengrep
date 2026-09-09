def consume(value):
    # ok: mapping-flow
    sink(value)
def invoke(consume):
    callback = consume
    callback(source())
invoke(lambda value: None)
