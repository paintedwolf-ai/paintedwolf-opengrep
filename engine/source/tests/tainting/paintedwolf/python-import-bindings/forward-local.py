from trusted import source
def helper():
    # ok: binding
    source()
    def source():
        return "fixed"
