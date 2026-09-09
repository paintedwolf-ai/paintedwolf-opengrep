word=decode(shlex.quote(source()))
# ruleid: flow
os.system("printf %s " + word)
