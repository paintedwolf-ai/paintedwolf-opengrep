def execute(value, count):
    if count > 0:
        return dispatch(value, count - 1)
    return value

def dispatch(value, count):
    if count > 0:
        return execute(value, count - 1)
    return value

unused = source()
# ok: recursive-flow
sink(dispatch("safe", 2))
