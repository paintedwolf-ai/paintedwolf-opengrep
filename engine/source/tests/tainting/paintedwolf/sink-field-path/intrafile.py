def consume(options):
    # ruleid: flow
    sink(options)
consume({"url": source(), "body": "safe"})

def consume_safe(options):
    sink(options)
consume_safe({"url": "https://example.com/", "body": source()})

def make_options(value):
    return {"url": value}
# ruleid: flow
sink(make_options(source()))

def make_safe(value):
    return {"url": "https://example.com/", "body": value}
sink(make_safe(source()))
