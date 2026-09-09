def handler():
 x = source()
 if condition():
  x = opaque(source())
 if x in {"status", "version"}:
  # ruleid: flow
  sink(x)
