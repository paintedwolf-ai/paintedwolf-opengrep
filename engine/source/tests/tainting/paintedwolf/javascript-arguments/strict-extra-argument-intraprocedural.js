'use strict';
function select(a) { return arguments[1]; }
// ruleid: flow
sink(select('safe', source()));
