function dispatch(value, count) {
  if (count <= 0) {
    // ok: recursive-context
    sink(value);
    return;
  }
  execute('safe', count - 1);
}
function execute(value, count) { dispatch(value, count); }
dispatch('safe', 1);
