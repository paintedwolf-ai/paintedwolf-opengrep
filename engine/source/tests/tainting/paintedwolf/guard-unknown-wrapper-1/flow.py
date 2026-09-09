def handler():
 x = opaque(source())
 if x in {"status", "version"}:
  # ruleid: flow
  sink(x)
