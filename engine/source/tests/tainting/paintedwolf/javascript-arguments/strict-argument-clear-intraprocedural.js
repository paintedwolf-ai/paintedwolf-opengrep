'use strict';
function run(a) {
  arguments[0] = 'safe';
  // ok: flow
  sink(arguments[0]);
}
run(source());
