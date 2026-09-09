'use strict';
// ruleid: formals
function f(value) {
  // ruleid: argument-syntax
  sink(arguments[0]);
}
f(source());
