import {exec as execute, execFile as unrelated} from "node:child_process";
import {exec} from "child_process";
import * as process from "node:child_process";
import fs from "node:fs";
import express, {Router as createRouter, json as notRouter} from "express";
// ruleid: shell-export
execute("command");
// ruleid: shell-export
exec("command");
// ruleid: shell-export
process.exec("command");
// ruleid: shell-export
process["exec"]("command");
unrelated("command");
process.execFile("command");
process[unknown]("command");
// ruleid: nested-export
fs.promises.readFile("path");
// ruleid: nested-export
fs["promises"]["readFile"]("path");
fs.readFile("path");
// ruleid: module-root
express();
// ruleid: router-export
express.Router();
// ruleid: router-export
createRouter();
notRouter();
express.json();
const {exec: launch, execFile: safe} = require("node:child_process");
// ruleid: shell-export
launch("command");
safe("command");
const factory = require("express");
// ruleid: module-root
factory();
// ruleid: router-export
factory.Router();
const {Router: router, json: helper} = require("express");
// ruleid: router-export
router();
helper();
function local(execute) { execute("command"); }
function sameModule() {
  const {execFile: execute} = require("node:child_process");
  execute("command");
}
function shadowedRequire(require) {
  const {exec: launch} = require("node:child_process");
  launch("command");
}
let {exec: replaced} = require("child_process");
replaced = value => value;
// Declaration identity survives a value write; API models must check the value.
// ruleid: shell-export
replaced("command");
