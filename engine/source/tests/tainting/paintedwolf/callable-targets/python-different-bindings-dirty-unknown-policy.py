def run(flag):
    first = lambda a,b: a
    second = lambda b,a: a
    helper = first if flag else second
    # ruleid: closure-context
    sink(helper("safe", source()))
