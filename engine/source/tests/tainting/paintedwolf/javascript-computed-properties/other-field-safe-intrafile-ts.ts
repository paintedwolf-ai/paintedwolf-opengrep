const object = { ["payload"]: source(), safe: "safe" };
// ok: computed-properties
sink(object.safe);
