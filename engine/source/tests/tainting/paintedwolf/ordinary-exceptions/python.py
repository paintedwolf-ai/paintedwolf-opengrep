def caught():
    try:
        raise ValueError(source())
    except ValueError as problem:
        # ruleid: flow
        sink(problem)


def safe_caught():
    unused = source()
    try:
        raise ValueError("safe")
    except ValueError as problem:
        sink(problem)


def reraised():
    try:
        try:
            raise ValueError(source())
        except ValueError:
            raise
    except ValueError as problem:
        # ruleid: flow
        sink(problem)


def chained():
    try:
        raise ValueError("safe") from source()
    except ValueError as problem:
        # ruleid: flow
        sink(problem.__cause__)


def discarded_binding():
    try:
        raise ValueError(source())
    except ValueError as problem:
        saved = problem
    # ruleid: flow
    sink(saved)
    sink(problem)


def implicit_context():
    try:
        try:
            raise ValueError(source())
        except ValueError:
            raise RuntimeError("safe") from None
    except RuntimeError as problem:
        # ruleid: flow
        sink(problem.__context__)
        sink(problem.__cause__)
