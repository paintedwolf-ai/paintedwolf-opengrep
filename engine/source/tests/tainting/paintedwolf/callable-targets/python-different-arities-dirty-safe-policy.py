def run(flag):
    first = lambda a: "safe"
    second = lambda b,a: a
    helper = first if flag else second
    # ruleid: closure-context
    sink(helper("safe", source()))
