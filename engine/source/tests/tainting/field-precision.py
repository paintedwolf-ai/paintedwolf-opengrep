def handler():
    fields = {"safe": "fixed", "unsafe": source()}
    # ok: field-precision
    sink(fields["safe"])
    # ruleid: field-precision
    sink(fields["unsafe"])
    # ruleid: field-precision
    sink(fields)
    nested = {"inner": fields}
    # ok: field-precision
    sink(nested["inner"]["safe"])
    # ruleid: field-precision
    sink(nested["inner"]["unsafe"])
    spread = {**fields}
    # ruleid: field-precision
    sink(spread["unsafe"])
    sequence = ["fixed", source()]
    # ok: field-precision
    sink(sequence[0])
    # ruleid: field-precision
    sink(sequence[1])
    # ruleid: field-precision
    sink(sequence)
    # ruleid: field-precision
    sink(fields[unknown()])
