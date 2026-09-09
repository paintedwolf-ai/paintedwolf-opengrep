import express from "express";
const app = express();
const copied = app;
// ruleid: express-flow
copied.get("/", req => eval(req.query.code));
const fake = unrelated(express());
fake.get("/", req => eval(req.query.code));
const text = "prefix" + app;
text.get("/", req => eval(req.query.code));
const collection = [express()];
collection.get("/", req => eval(req.query.code));
const legitimate = () => app;
// ruleid: express-flow
legitimate().get("/", req => eval(req.query.code));
const held = {server: app};
// ruleid: express-flow
held.server.get("/", req => eval(req.query.code));
const nested = [app];
// ruleid: express-flow
nested[0].get("/", req => eval(req.query.code));
app.setting = "fixed";
// ruleid: express-flow
app.get("/", req => eval(req.query.code));
let rebound = app;
rebound = {};
rebound.get("/", req => eval(req.query.code));
let branch = app;
if (choose) branch = express();
// ruleid: express-flow
branch.get("/", req => eval(req.query.code));
let mixed = app;
if (choose) mixed = {};
mixed.get("/", req => eval(req.query.code));
const fromRequire = require("express");
const cjs = fromRequire();
// ruleid: express-flow
cjs.get("/", req => eval(req.query.code));
const fakeFactory = unrelated(fromRequire);
const fakeCjs = fakeFactory();
fakeCjs.get("/", req => eval(req.query.code));
const changed = express();
changed.get = function(path, callback) { return "fixed"; };
changed.get("/", req => eval(req.query.code));
const changedAlias = express();
const methodAlias = changedAlias;
methodAlias["get"] = function(path, callback) { return "fixed"; };
changedAlias.get("/", req => eval(req.query.code));
function håndler(réq) {
  // ruleid: express-flow
  eval(réq.query.code);
}
app.get("/unicode", håndler);
const {Router: makeRouter} = require("express");
const router = makeRouter();
// ruleid: express-flow
router.get("/", req => eval(req.query.code));
const counterfeit = makeRouter.Router();
counterfeit.get("/", req => eval(req.query.code));
const {json: makeMiddleware} = require("express");
const middleware = makeMiddleware();
middleware.get("/", req => eval(req.query.code));
