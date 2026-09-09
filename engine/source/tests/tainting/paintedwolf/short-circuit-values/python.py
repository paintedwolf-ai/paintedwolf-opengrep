safe = True or source()
sink(safe)
unsafe = False or source()
# ruleid: flow
sink(unsafe)
safe_and = False and source()
sink(safe_and)
unsafe_and = True and source()
# ruleid: flow
sink(unsafe_and)
True or sink(source())
False and sink(source())
# ruleid: flow
False or sink(source())
# ruleid: flow
True and sink(source())
chained_safe = False and source() and source()
sink(chained_safe)
chained_or = True or source() or source()
sink(chained_or)
chained_unsafe = False or False or source()
# ruleid: flow
sink(chained_unsafe)
input_value = source()
retained_safe = True or input_value
sink(retained_safe)
discarded = False and input_value
sink(discarded)
returned = False or input_value
# ruleid: flow
sink(returned)
selected = False or {"unsafe": source(), "safe": "fixed"}
sink(selected["safe"])
# ruleid: flow
sink(selected["unsafe"])
