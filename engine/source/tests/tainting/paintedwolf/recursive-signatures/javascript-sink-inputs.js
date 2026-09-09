import express from 'express';
import { exec } from 'node:child_process';
const app = express();
function dispatch(command, count) { return execute(command, count - 1); }
function execute(command, count) {
  if (count > 0) return dispatch(command, count);
  // ruleid: recursive-flow
  exec(command);
}
app.get('/reports/run', (req, res) => {
  dispatch(req.query.command, 2);
  // ruleid: recursive-flow
  exec(req.query.direct);
  res.sendStatus(202);
});
