const cp = require("child_process");
let input = source();
const retained = source();
// ruleid: shell-flow
cp.execSync(input);
function clearInput() { input = "fixed"; }
clearInput();
cp.execSync(input);
// ruleid: shell-flow
cp.execSync(retained);
