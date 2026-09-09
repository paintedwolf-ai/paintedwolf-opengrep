const object = { ["payload"]: source(), payload: "safe" };
// ok: computed-properties
sink(object.payload);
