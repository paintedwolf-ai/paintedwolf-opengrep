const express = require("express");
const cp = require("node:child_process");
const app = express();
app.get("/unsafe", (request, response) => {
  // ruleid: express-shell
  cp.exec("echo " + request.query.name);
  cp.execFile("echo", [request.query.name]);
  cp.exec("echo fixed");
});
function named(request) {
  // ruleid: express-shell
  cp.execSync(request.params.command);
}
app.post("/run/:command", named);
function unrelated(request) { cp.exec(request.query.command); }
const own = {get(path, callback) { return "fixed"; }};
own.get("/", request => cp.exec(request.query.command));
app.get("/local", request => {
  const cp = {exec(value) { return value; }};
  cp.exec(request.query.command);
});
const {exec: launch} = require("child_process");
app.post("/body", (request, response) => {
  // ruleid: express-shell
  launch(request.body.command);
  launch(response.body.command);
  request.body.command = "fixed";
  launch(request.body.command);
});
