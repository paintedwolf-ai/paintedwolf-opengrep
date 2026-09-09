def helper(enabled):
    value = source()
    if enabled:
        # ruleid: flow
        sink(value)

register(helper)
helper(False)
