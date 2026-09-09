const key = source();
const object = { [key]: "safe" };
// ok: computed-properties
sink(object.payload);
