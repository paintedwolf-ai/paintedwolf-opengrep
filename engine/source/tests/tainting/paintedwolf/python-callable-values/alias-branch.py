def consume(value):
    # ruleid: mapping-flow
    sink(value)
if condition():
    callback = consume
else:
    callback = lambda value: None
callback(source())
