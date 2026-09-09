import create from "express";
import {Router as createRouter, json as createJson} from "express";
import * as namespace from "express";
const app = create();
app.post("/", (request, response) => {
  // ruleid: express-flow
  eval(request.body.code);
});
const router = createRouter();
router.put("/", function(request) {
  // ruleid: express-flow
  eval(request.params.code);
});
const namespaceRouter = namespace.Router();
namespaceRouter.use((request, response, next) => {
  // ruleid: express-flow
  eval(request.query.code);
});
const factory = require("express");
const commonjs = factory();
commonjs.delete("/", async (request, response) => {
  // ruleid: express-flow
  eval(request.body.code);
});
const commonRouter = factory.Router();
commonRouter.patch("/", function(request, response, next) {
  // ruleid: express-flow
  eval(request.query.code);
});
const {Router: routerFactory} = require("express");
const destructured = routerFactory();
destructured.all("/", (request) => {
  // ruleid: express-flow
  eval(request.params.code);
});
const alias = factory;
const aliasApp = alias();
aliasApp.get("/", (request, response) => {
  // ruleid: express-flow
  eval(request.query.code);
});
let replaceable = require("express");
replaceable = () => ({});
const fakeApp = replaceable();
fakeApp.get("/", (request, response) => { eval(request.query.code); });
const fakeFactoryResult = unrelated(factory);
fakeFactoryResult.get("/", (request, response) => { eval(request.query.code); });
const middleware = createJson();
middleware.get("/", (request, response) => { eval(request.query.code); });
const commonMiddleware = factory.json();
commonMiddleware.get("/", (request, response) => { eval(request.query.code); });
function localRequire(require) {
  const create = require("express");
  const server = create();
  server.get("/", (request, response) => { eval(request.query.code); });
}
function localFactory(create) {
  const server = create();
  server.get("/", (request, response) => { eval(request.query.code); });
}
function localApp(app) {
  app.get("/", (request, response) => { eval(request.query.code); });
}
app.notARoute("/", (request, response) => { eval(request.query.code); });
app.get("/", (request, response) => {
  request.query.code = "1+1";
  eval(request.query.code);
});
