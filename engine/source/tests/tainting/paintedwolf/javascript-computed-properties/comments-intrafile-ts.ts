// const object = { ["payload"]: source() }; sink(object.payload);
/* const object = { ["payload"]: source() }; sink(object.payload); */
const object = { ["payload"]: "safe" };
// ok: computed-properties
sink(object.payload);
