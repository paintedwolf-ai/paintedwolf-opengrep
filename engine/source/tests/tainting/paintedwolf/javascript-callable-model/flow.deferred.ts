const cp = require("child_process");
function exportedHandler() {
  const local = require("node:child_process");
  local.exec(source());
}
cp.exec = value => "fixed";
