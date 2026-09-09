def prepare(value):
    def consume():
        # ruleid: mapping-flow
        sink(value)
    def replace():
        nonlocal value
        value = source()
    return consume, replace
callback, replace = prepare("safe")
replace()
callback()
