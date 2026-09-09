function derive(value) {
  return mark(value);
}
function consume(value) {
  // ruleid: recursive-flow
  sink(derive(value));
}
function feed(left, right) {
  consume(left);
  consume(right);
}
feed("safe", source());
function consumeClean(value) {
  // ok: recursive-flow
  sink(derive(value));
}
function feedClean(left, right) {
  consumeClean(left);
  consumeClean(right);
}
feedClean("safe", "safe");
