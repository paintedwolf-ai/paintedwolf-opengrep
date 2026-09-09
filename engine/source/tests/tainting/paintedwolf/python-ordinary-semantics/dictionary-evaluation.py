def evaluation_order():
    value = source()
    mapped = {"value": value, "later": (value := "safe")}
    # ruleid: flow
    sink(mapped["value"])
    sink(mapped["later"])

    key = "value"
    keyed = {key: source(), (key := "other"): "safe"}
    # ruleid: flow
    sink(keyed["value"])
    sink(keyed["other"])

    original = {"value": source(), "other": "safe"}
    snapshot = {**original, "later": (original := {"value": "safe"})}
    # ruleid: flow
    sink(snapshot["value"])
    sink(snapshot["other"])
    sink(original["value"])


def unknown_overwrites(other):
    original = {**source(), "value": "safe"}
    copied = {**original}
    sink(copied["value"])
    # ruleid: flow
    sink(copied["unmentioned"])

    mixed = {**source(), **other}
    # ruleid: flow
    sink(mixed["value"])

    narrowed = {**source(), **{"value": "safe"}}
    sink(narrowed["value"])
    # ruleid: flow
    sink(narrowed["unmentioned"])


def copy_helper(mapping):
    return {**mapping}


def helper_call():
    copied = copy_helper({"value": source(), "other": "safe"})
    # ruleid: flow
    sink(copied["value"])
    sink(copied["other"])
