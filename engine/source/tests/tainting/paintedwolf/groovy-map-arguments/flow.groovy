def command(Map args, String ignored) { return args.script }
def positional(Map args, String text) { return text }
// ruleid: flow
sink(command(script: source(), "fixed"))
// ruleid: flow
sink(command("fixed", script: source()))
sink(command(script: "fixed", source()))
sink(command(other: source(), script: "fixed", "fixed"))
// ruleid: flow
sink(positional(script: "fixed", source()))
sink(positional(script: source(), "fixed"))
def unsafe = [script: source(), other: "fixed"]
// ruleid: flow
sink(unsafe.script)
// ruleid: flow
sink(unsafe["script"])
sink(unsafe.other)
sink(unsafe["other"])
def script = source()
def literalKey = [script: "fixed"]
sink(literalKey.script)
def dynamicKey = [("script"): source()]
// ruleid: flow
sink(dynamicKey["script"])
sink([script: "fixed"])
sink(1)
sink(0xff)
sink(1.25G)
