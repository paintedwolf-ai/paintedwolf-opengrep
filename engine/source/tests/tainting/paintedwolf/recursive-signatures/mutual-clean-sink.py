def dispatch(value, count):
    if count > 0:
        return execute(value, count - 1)
    return execute(value, 0)

def execute(value, count):
    if count > 0:
        return dispatch(value, count - 1)
    # ok: recursive-flow
    sink("safe")

dispatch(source(), 2)
