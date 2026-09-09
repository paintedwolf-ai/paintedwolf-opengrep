def unsafe_query(query):
    # ruleid: flow
    sink(query)
unsafe_query([source(), "bound"])

def safe_query(query):
    sink(query)
safe_query(["SELECT ?", source()])

def forwarded_query(query):
    # ruleid: flow
    sink(query)
def forward(query):
    forwarded_query(query)
forward([source(), "bound"])

def build_unsafe_query(value):
    return [value, "bound"]
# ruleid: flow
sink(build_unsafe_query(source()))

def build_safe_query(value):
    return ["SELECT ?", value]
sink(build_safe_query(source()))
