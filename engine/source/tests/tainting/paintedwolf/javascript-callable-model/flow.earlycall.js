const cp = require("child_process");
function handler() {
  const local = require("node:child_process");
  // ruleid: shell-flow
  local.exec(source());
}
handler();
cp.exec = value => "fixed";
handler();
