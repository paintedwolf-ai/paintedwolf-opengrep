def sequences():
    values = [source(), "safe", "safe"]
    first = values[:1]
    # ruleid: flow
    sink(first[0])
    tail = values[1:]
    sink(tail[0])
    reversed_values = values[::-1]
    sink(reversed_values[0])
    # ruleid: flow
    sink(reversed_values[2])
    backwards = values[-3:-2]
    # ruleid: flow
    sink(backwards[0])
    empty = values[1:1]
    sink(empty)
    skipped = values[1::2]
    sink(skipped)
    string = source()
    # ruleid: flow
    sink(string[1:])
    # ruleid: flow
    sink(values[source():])
