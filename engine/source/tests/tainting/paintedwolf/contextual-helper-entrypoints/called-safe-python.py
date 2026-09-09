def helper(enabled):
    value = source()
    if enabled:
        # ok: flow
        sink(value)

helper(False)
