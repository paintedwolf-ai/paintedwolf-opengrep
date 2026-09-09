const cp = require("child_process");
const retained = cp.exec;
cp.exec = value => "fixed";
const again = require("node:child_process");
again.exec(source());
// ruleid: shell-flow
retained(source());
// ruleid: shell-flow
again.execSync(source());
