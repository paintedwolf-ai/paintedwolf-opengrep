function dispatch(value, count) {
  if (count <= 0) {
    // ok: recursive-context
    sink(value);
    return;
  }
  dispatch('safe', count - 1);
}
dispatch('safe', 1);
