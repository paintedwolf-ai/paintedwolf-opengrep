def handler():
 x = source()
 if x in {"status", "version"}:
  # ruleid: flow
  sink(x)
