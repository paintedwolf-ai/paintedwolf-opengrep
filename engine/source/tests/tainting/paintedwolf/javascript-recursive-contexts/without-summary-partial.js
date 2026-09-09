function dispatch(value, count) {
  if (count <= 0) {
    // ruleid: recursive-context
    sink(value);
    return;
  }
  execute(value, count - 1);
}
function execute(value, count) { dispatch(value, count); }
dispatch(source(), 1);
// ruleid: recursive-context
sink(source());
