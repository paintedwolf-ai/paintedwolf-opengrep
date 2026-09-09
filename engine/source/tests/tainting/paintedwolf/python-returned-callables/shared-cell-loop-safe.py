def prepare(value):
    def consume():
        # ok: mapping-flow
        sink(value)
    def replace(replacement):
        nonlocal value
        value = replacement
    return consume, replace
unrelated = source()
saved = None
for index in sequence:
    reader, replace = prepare("safe")
    if saved is not None:
        replace("safe")
        saved()
    saved = reader
