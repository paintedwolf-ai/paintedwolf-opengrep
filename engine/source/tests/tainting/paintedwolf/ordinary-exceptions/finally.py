def normal_completion():
    value = source()
    try:
        pass
    finally:
        value = "safe"
    sink(value)


def captured_return():
    value = source()
    try:
        return value
    finally:
        value = "safe"


# ruleid: flow
sink(captured_return())


def overridden_return():
    try:
        return source()
    finally:
        return "safe"


sink(overridden_return())


def throw_overridden_by_return():
    try:
        raise ValueError(source())
    finally:
        return "safe"


sink(throw_overridden_by_return())


def break_cleanup():
    value = source()
    while True:
        try:
            break
        finally:
            value = "safe"
    sink(value)


def continue_cleanup():
    for item in items:
        value = source()
        try:
            continue
        finally:
            # ruleid: flow
            sink(value)
            value = "safe"
            sink(value)


def nested_order():
    value = "safe"
    try:
        try:
            return value
        finally:
            value = source()
    finally:
        # ruleid: flow
        sink(value)


def catch_cleanup_on_return():
    try:
        try:
            raise ValueError(source())
        except ValueError as error:
            return error
    finally:
        sink("safe")


# ruleid: flow
sink(catch_cleanup_on_return())


def throw_overrides_return():
    try:
        return "safe"
    finally:
        raise ValueError(source())


def caller_of_throwing_finalizer():
    try:
        throw_overrides_return()
    except ValueError as error:
        # ruleid: flow
        sink(error)
