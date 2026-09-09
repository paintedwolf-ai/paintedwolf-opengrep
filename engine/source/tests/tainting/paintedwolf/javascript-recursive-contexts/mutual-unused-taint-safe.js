function dispatch(ignored, value, count) {
  if (count <= 0) {
    // ok: recursive-context
    sink(value);
    return;
  }
  execute(ignored, 'safe', count - 1);
}
function execute(ignored, value, count) { dispatch(ignored, value, count); }
dispatch(source(), 'safe', 1);
