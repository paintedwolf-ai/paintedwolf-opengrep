let key = "payload";
const object = { [key]: (key = "safe", source()) };
// ruleid: computed-properties
sink(object.payload);
