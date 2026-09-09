word=shlex.quote(source())
# ruleid: flow
os.system("sh -c " + word)
