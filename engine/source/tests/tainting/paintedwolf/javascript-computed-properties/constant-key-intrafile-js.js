const key = "payload";
const object = { [key]: source() };
// ruleid: computed-properties
sink(object.payload);
