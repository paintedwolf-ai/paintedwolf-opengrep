value = source()
if condition():
    value = {"text": "safe"}
value["text"] = "safe"
# ok: mapping-flow
sink(value["text"])
