'use strict';
function select(a) {
  const inner = () => arguments[0];
  return inner('safe');
}
// ruleid: flow
sink(select(source()));
