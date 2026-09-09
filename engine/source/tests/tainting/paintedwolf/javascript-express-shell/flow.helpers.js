import express from "express";
import {exec as launch} from "node:child_process";
function command() { return copied; }
const copied = launch;
const app = express();
app.get("/", request => {
  // ruleid: express-shell
  copied(request.query.command);
  // ruleid: express-shell
  command()(request.query.command);
});
