value = "safe"
if condition():
    value = {"text": "safe"}
# ok: mapping-flow
sink(value["text"])
