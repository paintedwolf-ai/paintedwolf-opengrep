def prepare(value):
    def consume():
        # ruleid: mapping-flow
        sink(value)
    def replace():
        nonlocal value
        value = source()
        raise ValueError("done")
    return consume, replace
callback, replace = prepare("safe")
try:
    replace()
except ValueError:
    pass
callback()
