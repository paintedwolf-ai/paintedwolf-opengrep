def select(values):
    return values["bad"]

# ruleid: flow
sink(select({"bad": source(), "good": "safe"}))
# ok: flow
sink(select({"bad": "safe", "good": source()}))
