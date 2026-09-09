function dispatch(value, count) {
  if (count <= 0) {
    // ruleid: recursive-context
    sink(value);
    return;
  }
  dispatch(source(), count - 1);
}
dispatch('safe', 1);
