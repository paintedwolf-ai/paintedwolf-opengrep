function helper(enabled) {
  const value = source();
  if (enabled) {
    // ok: flow
    sink(value);
  }
}
helper(false);
