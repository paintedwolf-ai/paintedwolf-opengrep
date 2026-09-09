def mappings():
    incoming = {"value": source(), "other": "safe"}
    copied = {**incoming}
    # ruleid: flow
    sink(copied["value"])
    sink(copied["other"])
    overwritten = {**incoming, "value": "safe"}
    sink(overwritten["value"])
    restored = {"value": "safe", **incoming}
    # ruleid: flow
    sink(restored["value"])
    final = {**incoming, **{"value": "safe"}}
    sink(final["value"])
    dirty = {**{"value": "safe"}, **incoming}
    # ruleid: flow
    sink(dirty["value"])
    unknown = {**source()}
    # ruleid: flow
    sink(unknown["value"])
    unknown_after = {"value": "safe", **source()}
    # ruleid: flow
    sink(unknown_after["value"])
    known_after = {**source(), "value": "safe"}
    sink(known_after["value"])
