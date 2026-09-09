'use strict';
function consume(value) {
  // ruleid: flow
  sink(value);
}
function invoke() { arguments[0](arguments[1]); }
invoke(consume, source());
