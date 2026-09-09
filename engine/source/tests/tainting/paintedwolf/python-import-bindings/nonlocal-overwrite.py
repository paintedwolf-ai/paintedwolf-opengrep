def outer():
    from trusted import source
    def inner():
        nonlocal source
        source = local
        # ok: binding
        source()
