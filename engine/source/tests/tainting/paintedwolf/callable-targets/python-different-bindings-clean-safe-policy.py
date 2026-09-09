def run(flag):
    first = lambda a,b: a
    second = lambda b,a: b
    helper = first if flag else second
    # ok: closure-context
    sink(helper("safe", source()))
