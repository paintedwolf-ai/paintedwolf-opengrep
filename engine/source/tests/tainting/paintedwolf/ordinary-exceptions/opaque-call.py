def relay(value):
    external(value)


def through_helper():
    value = source()
    try:
        relay(value)
    except Exception as problem:
        sink(problem)


def unused():
    value = source()
    try:
        external(value)
    except Exception as unused:
        sink("safe")


def optional():
    value = source()
    try:
        external(value)
    except:
        sink("safe")


def context_projection():
    value = source()
    try:
        try:
            external(value)
        except:
            raise RuntimeError("safe")
    except RuntimeError as problem:
        sink(problem.__context__.message)


def overwritten_unknown_member():
    value = source()
    try:
        external(value)
    except Exception as problem:
        problem.message = "safe"
        sink(problem.message)
        sink(problem.other)
