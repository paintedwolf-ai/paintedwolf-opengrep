def handler():
 x = source()
 y = source()
 if x in {"status", "version"}:
  # ruleid: flow
  sink(y)
