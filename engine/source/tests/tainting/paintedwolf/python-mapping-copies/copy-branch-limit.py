def copy(mapping):
    value = mapping
    if condition():
        value = {**value, "left0": "safe"}
    else:
        value = {**value, "right0": "safe"}
    if condition():
        value = {**value, "left1": "safe"}
    else:
        value = {**value, "right1": "safe"}
    if condition():
        value = {**value, "left2": "safe"}
    else:
        value = {**value, "right2": "safe"}
    if condition():
        value = {**value, "left3": "safe"}
    else:
        value = {**value, "right3": "safe"}
    if condition():
        value = {**value, "left4": "safe"}
    else:
        value = {**value, "right4": "safe"}
    if condition():
        value = {**value, "left5": "safe"}
    else:
        value = {**value, "right5": "safe"}
    if condition():
        value = {**value, "left6": "safe"}
    else:
        value = {**value, "right6": "safe"}
    if condition():
        value = {**value, "left7": "safe"}
    else:
        value = {**value, "right7": "safe"}
    if condition():
        value = {**value, "left8": "safe"}
    else:
        value = {**value, "right8": "safe"}
    if condition():
        value = {**value, "left9": "safe"}
    else:
        value = {**value, "right9": "safe"}
    return value
value = copy({"tainted": source()})
# ruleid: mapping-flow
sink(value["tainted"])
