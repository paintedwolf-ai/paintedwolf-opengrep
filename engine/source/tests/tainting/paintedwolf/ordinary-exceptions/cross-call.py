def clean_raiser(value):
    raise ValueError("safe")


def tainted_raiser(value):
    raise ValueError(value)


def through_calls():
    try:
        clean_raiser(source())
    except ValueError as problem:
        sink(problem)
    try:
        tainted_raiser(source())
    except ValueError as problem:
        # ruleid: flow
        sink(problem)


def forwarding_helper(value):
    tainted_raiser(value)


def through_two_calls():
    value = source()
    try:
        forwarding_helper(value)
    except ValueError as problem:
        # ruleid: flow
        sink(problem)
