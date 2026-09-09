function test(object) {
  const input = source();
  // ok: delete-evaluation
  sink(delete object.field);
}
