def handler(request):
    # ruleid: flow
    sink(request)
    alias = request
    # ruleid: flow
    sink(alias)
    # ok: flow
    sink(request.context)
    request = None
    # ok: flow
    sink(request)
