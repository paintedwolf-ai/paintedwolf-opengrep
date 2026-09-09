value = source()
if condition():
    value = {"text": "safe"}
# ruleid: mapping-flow
sink(value["text"])
