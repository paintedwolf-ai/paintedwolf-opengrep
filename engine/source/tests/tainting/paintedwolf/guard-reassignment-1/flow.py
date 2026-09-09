def handler():
 x = source()
 if x in {"status", "version"}:
  x = source()
  # ruleid: flow
  sink(x)
