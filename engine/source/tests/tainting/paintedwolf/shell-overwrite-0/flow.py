word=shlex.quote(source())
word=source()
# ruleid: flow
os.system("printf %s " + word)
