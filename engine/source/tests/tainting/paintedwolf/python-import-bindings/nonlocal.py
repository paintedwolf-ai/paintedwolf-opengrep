def outer():
    from trusted import source
    def inner():
        nonlocal source
        # ruleid: binding
        source()
