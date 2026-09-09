def consume(value):
    # ruleid: mapping-flow
    sink(value)
def handle(value):
    callback = consume
    callback(value)
handle(source())
