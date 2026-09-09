def prepare(value):
    def consume():
        # ruleid: mapping-flow
        sink(value)
    def replace(replacement):
        nonlocal value
        value = replacement
    return consume, replace
callback, replace = prepare(source())
if unknown():
    replace("safe")
callback()
