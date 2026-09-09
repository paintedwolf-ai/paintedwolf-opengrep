# ruleid: flow
sink(make_model())
model = make_model()
# ruleid: flow
sink(model)
# ruleid: flow
sink((make_model()))
# ok: flow
sink("safe")
# ok: flow
sink(other_factory())
# ok: flow
sink([make_model()])
# ok: flow
sink(opaque(make_model()))
