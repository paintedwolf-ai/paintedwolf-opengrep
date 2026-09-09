function helper(enabled) {
  const value = source();
  if (enabled) {
    // ruleid: flow
    sink(value);
  }
}
register(helper);
helper(false);
