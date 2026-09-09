const object = { payload: "safe", ["payload"]: source() };
// ruleid: computed-properties
sink(object.payload);
