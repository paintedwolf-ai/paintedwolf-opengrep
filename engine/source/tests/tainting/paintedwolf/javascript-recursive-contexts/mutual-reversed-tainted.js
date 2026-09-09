function execute(value, count) { dispatch(value, count); }
function dispatch(value, count) {
  if (count <= 0) {
    // ruleid: recursive-context
    sink(value);
    return;
  }
  execute(source(), count - 1);
}
dispatch('safe', 1);
