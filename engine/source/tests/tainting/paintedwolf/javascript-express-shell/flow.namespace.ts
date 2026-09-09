import express from "express";
import process from "node:child_process";
import * as namespace from "node:child_process";
import {exec} from "node:child_process";
const app = express();
process.exec = value => "fixed";
app.get("/", request => {
  process.exec(request.query.command);
  // ruleid: express-shell
  namespace.exec(request.query.command);
  // ruleid: express-shell
  exec(request.query.command);
});
