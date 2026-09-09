value = {"text": "safe"}
if condition():
    value = source()
# ruleid: mapping-flow
sink(value["text"])
