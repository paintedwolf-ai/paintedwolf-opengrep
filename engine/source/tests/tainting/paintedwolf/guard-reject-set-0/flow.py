def handler():
 x = source()
 if x not in {"status", "version"}:
  return
 sink(x)
