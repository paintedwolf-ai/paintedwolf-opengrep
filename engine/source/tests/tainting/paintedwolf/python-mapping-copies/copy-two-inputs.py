def copy(first, second):
    return {**first, **second}
value = copy({"value": source(), "left": source()}, {"value": "safe", "right": "safe"})
sink(value["value"])
# ruleid: mapping-flow
sink(value["left"])
sink(value["right"])
