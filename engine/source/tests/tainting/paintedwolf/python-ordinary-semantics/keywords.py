def pick(value="safe", other="safe"):
    return value

# ruleid: flow
sink(pick(**{"value": source(), "other": "safe"}))
sink(pick(**{"value": "safe", "other": source()}))

values = {"value": source()}
# ruleid: flow
sink(pick(**values))

sink(pick("safe", **{"other": source()}))

def remaining(value="safe", **kwargs):
    return kwargs["other"]

# ruleid: flow
sink(remaining(value="safe", other=source()))
sink(remaining(value=source(), other="safe"))
# ruleid: flow
sink(remaining(**{"value": "safe", "other": source()}))
sink(remaining(**{"value": source(), "other": "safe"}))

def keyword_name(**kwargs):
    return kwargs["kwargs"]

# ruleid: flow
sink(keyword_name(kwargs=source()))
