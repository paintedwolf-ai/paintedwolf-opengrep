'use strict';
function select(a) {
  function inner() { return arguments[0]; }
  return inner('safe');
}
// ok: flow
sink(select(source()));
