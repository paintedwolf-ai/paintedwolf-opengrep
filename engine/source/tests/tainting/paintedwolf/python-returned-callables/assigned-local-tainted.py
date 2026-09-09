def prepare():
    def consume():
        # ruleid: mapping-flow
        sink(local)
    local = source()
    return consume
callback = prepare()
callback()
