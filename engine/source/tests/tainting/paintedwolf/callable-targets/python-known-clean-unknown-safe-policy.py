def run(flag):
    first = lambda a: "safe"
    second = unknown_factory()
    helper = first if flag else second
    # ok: closure-context
    sink(helper(source()))
