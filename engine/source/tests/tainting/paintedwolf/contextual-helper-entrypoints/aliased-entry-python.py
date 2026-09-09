def helper(enabled):
    value = source()
    if enabled:
        # ruleid: flow
        sink(value)

alias = helper
alias(True)
helper(False)
