def run(value):
    def consume():
        # ruleid: mapping-flow
        sink(value)
    value = source()
    consume()
run("safe")
