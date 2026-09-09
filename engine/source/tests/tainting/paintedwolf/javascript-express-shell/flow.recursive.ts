import express from "express";
import {exec} from "node:child_process";
function recursive() { return recursive(); }
const app = express();
app.get("/", request => {
  // ruleid: express-shell
  exec(request.query.command);
  recursive()(request.query.command);
});
