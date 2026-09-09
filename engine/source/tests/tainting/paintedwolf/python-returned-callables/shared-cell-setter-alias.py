def prepare(value):
    def consume():
        # ok: mapping-flow
        sink(value)
    def replace(replacement):
        nonlocal value
        value = replacement
    return consume, replace
callback, replace = prepare(source())
alias = replace
alias("safe")
callback()
