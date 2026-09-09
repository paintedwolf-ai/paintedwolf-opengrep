def dispatch(value, count):
    if count > 0:
        return execute(value, count - 1)
    return value

def execute(value, count):
    if count > 0:
        return dispatch(value, count - 1)
    return value

# ruleid: recursive-flow
sink(dispatch(source(), 2))
