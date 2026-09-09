function test(key) {
  const object = { payload: "safe", [key]: source() };
  // ruleid: computed-properties
  sink(object.payload);
}
