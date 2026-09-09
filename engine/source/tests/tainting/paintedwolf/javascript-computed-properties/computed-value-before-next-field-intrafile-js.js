let value = source();
const object = { ["payload"]: value, later: (value = "safe") };
// ruleid: computed-properties
sink(object.payload);
