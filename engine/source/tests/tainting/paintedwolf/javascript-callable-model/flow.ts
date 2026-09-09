const {exec: execute, execFile: safe} = require("node:child_process");
// ruleid: shell-flow
execute(source());
safe(source());
const alias = execute;
// ruleid: shell-flow
alias(source());
let {exec: replaced} = require("child_process");
replaced = value => "fixed";
replaced(source());
const cp = require("child_process");
// ruleid: shell-flow
cp.exec(source());
// ruleid: shell-flow
cp.execSync(source());
cp.execFile("printf", [source()]);
const fresh = require("child_process");
const held = fresh.exec;
// ruleid: shell-flow
held(source());
const changed = require("child_process");
changed.exec = value => "fixed";
changed.exec(source());
const changedAlias = changed.exec;
changedAlias(source());
const moduleAlias = require("node:child_process");
const copied = moduleAlias;
// The earlier member replacement is visible through the cached module.
copied.exec(source());
const unknown = unrelated(execute);
unknown(source());
function localRequire(require) {
  const {exec: local} = require("child_process");
  local(source());
}
function samePackage() {
  const {execFile: execute} = require("child_process");
  execute(source());
}
const clean = require("child_process");
clean.exec("printf fixed");
