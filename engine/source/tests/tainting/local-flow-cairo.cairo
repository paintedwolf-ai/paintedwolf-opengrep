fn direct() {
  // ruleid: local-flow
  sink(source());
}
fn local() {
  let value = source();
  // ruleid: local-flow
  sink(value);
}
fn shadow() {
  let value = source();
  let value = 123;
  // ok: local-flow
  sink(value);
}
