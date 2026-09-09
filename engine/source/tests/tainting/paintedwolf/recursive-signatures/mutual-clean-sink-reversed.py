def execute(value, count):
    if count > 0:
        return dispatch(value, count - 1)
    # ok: recursive-flow
    sink("safe")

def dispatch(value, count):
    if count > 0:
        return execute(value, count - 1)
    return execute(value, 0)

dispatch(source(), 2)
