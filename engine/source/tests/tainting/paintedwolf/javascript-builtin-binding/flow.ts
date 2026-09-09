// ruleid: global-eval
eval(source());
function parameter(eval) { eval(source()); }
function destructured({ eval }) { eval(source()); }
function rest(...eval) { eval(source()); }
function forward() {
  eval(source());
  function eval(value) { return value; }
}
function defaultValue(eval = source()) { eval(source()); }
function block() {
  { const eval = value => value; eval(source()); }
  // ruleid: global-eval
  eval(source());
}
function undefinedBinding(undefined) {
  const value = source();
  undefined = value;
  // ruleid: global-eval
  eval(undefined);
}
function trueUndefined() { eval(undefined); }
