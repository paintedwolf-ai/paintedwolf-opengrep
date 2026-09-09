function dispatch(value, count) {
  if (count <= 0) {
    // ruleid: recursive-context
    sink(value);
    return;
  }
  execute(source(), count - 1);
}
function execute(value, count) { dispatch(value, count); }
dispatch('safe', 1);
