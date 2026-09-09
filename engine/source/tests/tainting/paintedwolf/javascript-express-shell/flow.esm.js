import express from "express";
import {exec as launch, execFile as argumentsOnly} from "node:child_process";
import * as process from "node:child_process";
import child from "child_process";
const app = express();
app.get("/", request => {
  // ruleid: express-shell
  launch(request.query.command);
  // ruleid: express-shell
  process.execSync(request.query.command);
  // ruleid: express-shell
  child.exec(request.query.command);
  argumentsOnly("echo", [request.query.command]);
});
app.get("/shadow", request => {
  const launch = value => value;
  launch(request.query.command);
});
