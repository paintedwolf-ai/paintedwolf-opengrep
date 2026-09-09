def execute(value, count):
    if count > 0:
        return dispatch(value, count - 1)
    return "safe"

def dispatch(value, count):
    if count > 0:
        return execute(value, count - 1)
    return "safe"

# ok: recursive-flow
sink(dispatch(source(), 2))
