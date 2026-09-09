import express from "express";
const app = express();
function registered(req, res) {
  // ruleid: express-flow
  eval(req.query.code);
}
app.get("/", registered);
function unregistered(req, res) { eval(req.query.code); }
function localApp() {
  const app = {};
  function handler(req, res) { eval(req.query.code); }
  app.get("/", handler);
}
function shadowed(req, res) { eval(req.query.code); }
function anotherScope(shadowed) { app.get("/", shadowed); }
anotherScope((req, res) => {});
app.get("/after", after);
function after(req, res) {
  // ruleid: express-flow
  eval(req.query.code);
}
