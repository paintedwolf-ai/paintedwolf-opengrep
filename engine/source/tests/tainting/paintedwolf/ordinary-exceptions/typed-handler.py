def distinct_handlers():
    try:
        raise ValueError(source())
    except KeyError as unrelated:
        sink(unrelated)
    except ValueError as actual:
        # ruleid: flow
        sink(actual)


def first_matching_parent():
    try:
        raise KeyError(source())
    except LookupError as first:
        # ruleid: flow
        sink(first)
    except KeyError as later:
        sink(later)


def correlated_payloads(condition):
    try:
        if condition:
            raise ValueError("safe")
        else:
            raise KeyError(source())
    except ValueError as safe:
        sink(safe)
    except KeyError as unsafe:
        # ruleid: flow
        sink(unsafe)


def quiet_sibling_fields():
    try:
        raise ValueError(source())
    except ValueError as error:
        sink(error.__cause__)
        # ruleid: flow
        sink(error.args[0])


def tuple_handlers():
    value = source()
    try:
        raise KeyError(value)
    except (TypeError, ValueError) as unrelated:
        sink(unrelated)
    except (LookupError,) as actual:
        # ruleid: flow
        sink(actual)
