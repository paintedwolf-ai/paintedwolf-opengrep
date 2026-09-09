# ruleid: flow
register(lambda request: sink(request) if request in {"status", "version"} else None)
