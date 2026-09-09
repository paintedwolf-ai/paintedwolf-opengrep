const cp = require("child_process");
function replaceCached() {
  const same = require("node:child_process");
  same.exec = value => "fixed";
}
replaceCached();
const again = require("child_process");
again.exec(source());
