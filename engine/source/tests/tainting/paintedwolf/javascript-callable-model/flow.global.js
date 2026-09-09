const cp = require("child_process");
cp.exec = value => "fixed";
function handler() {
  const local = require("node:child_process");
  local.exec(source());
}
handler();
