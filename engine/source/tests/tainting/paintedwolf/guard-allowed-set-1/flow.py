def handler():
 x = source()
 if x in {"status", "version"}:
  sink(x)
