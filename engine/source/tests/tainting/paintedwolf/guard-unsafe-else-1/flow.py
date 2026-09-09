def handler():
 x = source()
 if x in {"status", "version"}:
  pass
 else:
  # ruleid: flow
  sink(x)
