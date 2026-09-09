const cp = require("child_process");
function unused() { cp.exec = value => "fixed"; }
// ruleid: shell-flow
cp.exec(source());
