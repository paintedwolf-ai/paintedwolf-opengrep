def execute(value, count):
    if count > 0:
        return dispatch(value, count - 1)
    return value

def dispatch(value, count):
    return execute("safe", count - 1)

# ok: recursive-flow
sink(dispatch(source(), 2))
