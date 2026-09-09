function test(key) {
  const object = { payload: source(), [key]: "safe" };
  // ruleid: computed-properties
  sink(object.payload);
}
