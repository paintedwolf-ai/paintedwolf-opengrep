def raise_value(value):
    raise ValueError(value)


def literal_payload():
    try:
        raise_value("TAINTED")
    except ValueError as error:
        # ruleid: flow
        sink(error.args[0])


def field_payload(request):
    try:
        raise_value(request.payload)
    except ValueError as error:
        # ruleid: flow
        sink(error.args[0])


def safe_sibling(request):
    request.payload
    try:
        raise_value(request.fixed)
    except ValueError as error:
        # ok: flow
        sink(error.args[0])


def mutate_after_capture(original, box):
    box.value = "TAINTED"
    raise ValueError(original)


def argument_is_evaluated_before_call(box):
    box.value = "safe"
    try:
        mutate_after_capture(box.value, box)
    except ValueError as error:
        # ok: flow
        sink(error.args[0])
