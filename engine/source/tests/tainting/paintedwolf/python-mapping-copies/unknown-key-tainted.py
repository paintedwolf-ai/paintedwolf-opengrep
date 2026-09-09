fields = {"safe": "fixed", "unsafe": source()}
# ruleid: mapping-flow
sink(fields[unknown_key()])
