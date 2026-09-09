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
app.get("/after", after);
function after(req, res) {
  // ruleid: express-flow
  eval(req.query.code);
}
function aliasTarget(req, res) {
  // ruleid: express-flow
  eval(req.body.code);
}
const alias = aliasTarget;
app.post("/alias", alias);
const arrow = (req, res) => {
  // ruleid: express-flow
  eval(req.params.code);
};
app.put("/arrow", arrow);
function overwritten(req, res) { eval(req.query.code); }
let changed = overwritten;
changed = (req, res) => {};
app.get("/safe", changed);
app.get("/response", (req, res) => { eval(res.query.code); });
const destructured = ({query: values, app: application}, res) => {
  // ruleid: express-flow
  eval(values.code);
  eval(application.code);
};
app.get("/destructured", destructured);
app.get("/nested", ({body: {code}}, res) => {
  // ruleid: express-flow
  eval(code);
});
app.get("/default", ({query: values = {}}, res) => {
  // ruleid: express-flow
  eval(values.code);
});
app.get("/safe-field", ({app: application}, res) => { eval(application.code); });
app.get("/overwrite", (req, res) => { req.query = {}; eval(req.query.code); });
app.get("/error", (err, req, res, next) => {
  // ruleid: express-flow
  eval(req.body.code);
  eval(err.body.code);
  eval(res.body.code);
});
function propertyHandler(req, res) {
  // ruleid: express-flow
  eval(req.query.code);
}
const handlers = {show: propertyHandler};
app.get("/property", handlers.show);
function arrayHandler(req, res) {
  // ruleid: express-flow
  eval(req.query.code);
}
const routes = [arrayHandler];
app.get("/array", routes[0]);
function branchA(req, res) {
  // ruleid: express-flow
  eval(req.body.code);
}
function branchB(req, res) {
  // ruleid: express-flow
  eval(req.params.code);
}
let selected;
if (flag) { selected = branchA; } else { selected = branchB; }
app.get("/branch", selected);

app.get("/rest-object", ({app: application, ...req}, res) => {
  // ruleid: express-flow
  eval(req.query.code);
  eval(req.app.code);
});
app.get("/rest-arguments", (...args) => {
  // ruleid: express-flow
  eval(args[0].body.code);
  eval(args[1].body.code);
});
app.get("/default-arity", (req, res, next, optional = {}) => {
  // ruleid: express-flow
  eval(req.query.code);
  eval(res.query.code);
});

app.get("/header", ({headers}, res) => {
  // ruleid: express-flow
  eval(headers["x-code"]);
});
