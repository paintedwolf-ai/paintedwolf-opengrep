def prepare(value):
    def consume():
        # ok: mapping-flow
        sink(value)
    def replace(replacement):
        nonlocal value
        value = replacement
    return consume, replace
dangerous, _ = prepare(source())
clean, replace = prepare("safe")
replace("safe")
clean()
