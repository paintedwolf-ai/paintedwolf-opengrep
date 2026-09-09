function test() {
  let value = source();
  if (delete value) {
    // ok: delete-evaluation
    sink(source());
  }
}
