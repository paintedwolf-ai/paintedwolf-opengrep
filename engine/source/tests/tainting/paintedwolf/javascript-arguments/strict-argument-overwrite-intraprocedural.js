'use strict';
function run(a) {
  arguments[0] = 'safe';
  // ruleid: flow
  sink(a);
}
run(source());
