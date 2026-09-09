'use strict';
function select(a) { return arguments[1]; }
// ok: flow
sink(select(source()));
