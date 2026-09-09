def later(first="safe", second="safe", third="safe"):
    sink(first)
    # ruleid: flow
    sink(second)
    sink(third)
later(second=source())

def named_only(*, first="safe", second="safe"):
    sink(first)
    # ruleid: flow
    sink(second)
named_only(second=source())

def safe(first="safe", second="safe"):
    sink(second)
safe(first=source())
