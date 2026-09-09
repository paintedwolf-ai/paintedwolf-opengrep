def consume(value):
    # ok: mapping-flow
    sink(value)
def handle(value):
    callback = consume
    callback(value)
handle("safe")
