function test(key) {
  const object = { [key]: source() };
  // ruleid: computed-properties
  sink(object.payload);
}
