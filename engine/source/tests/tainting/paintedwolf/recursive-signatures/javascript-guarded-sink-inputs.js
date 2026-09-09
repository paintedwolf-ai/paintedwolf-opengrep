function select(left, right, first) {
  if (first) return left;
  return right;
}
function dispatch(left, right, count) {
  return execute(left, right, count - 1);
}
function execute(left, right, count) {
  if (count > 0) return dispatch(left, right, count);
  // ruleid: recursive-flow
  sink(select(left, right, true) + select(left, right, false));
}
dispatch(sourceA(), sourceB(), 2);
function dispatchOne(left, right, count) {
  return executeOne(left, right, count - 1);
}
function executeOne(left, right, count) {
  if (count > 0) return dispatchOne(left, right, count);
  // ok: recursive-flow
  sink(select(left, right, true) + select(left, right, false));
}
dispatchOne(sourceA(), "safe", 2);
