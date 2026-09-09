def handler():
 x = source()
 if x in {"status", "version"}:
  pass
 # ruleid: flow
 sink(x)
