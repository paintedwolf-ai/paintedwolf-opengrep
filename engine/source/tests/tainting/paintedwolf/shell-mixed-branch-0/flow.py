word=shlex.quote(source())
if condition():
 word=source()
# ruleid: flow
os.system("printf %s " + word)
