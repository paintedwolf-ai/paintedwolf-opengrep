from trusted import source
def helper():
    global source
    source = local
    # ok: binding
    source()
