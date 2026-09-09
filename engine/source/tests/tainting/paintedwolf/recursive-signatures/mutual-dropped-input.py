def dispatch(value, count):
    return execute("safe", count - 1)

def execute(value, count):
    if count > 0:
        return dispatch(value, count - 1)
    return value

# ok: recursive-flow
sink(dispatch(source(), 2))
