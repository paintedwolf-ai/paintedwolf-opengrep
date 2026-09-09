let value = "safe";
const object = { payload: value, later: (value = source()) };
// ok: computed-properties
sink(object.payload);
// ruleid: computed-properties
sink(object.later);
