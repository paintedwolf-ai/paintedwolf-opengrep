import express from "express";
const app = express();
function first(req, res) {
  // ruleid: express-flow
  eval(req.query.code);
  eval(res.query.code);
}
app.use(first);
app.use((req, res) => {
  // ruleid: express-flow
  eval(req.body.code);
});
function second(req, res) {
  // ruleid: express-flow
  eval(req.params.code);
}
app.use("/path", first, second);
function nested(req, res) {
  // ruleid: express-flow
  eval(req.headers.code);
}
app.use([first, [second, nested]]);
const middleware = [first, [nested]];
const alias = middleware;
app.post("/array", alias);
function propertyOnly(req, res) { eval(req.query.code); }
const arrayWithProperty = [first];
arrayWithProperty.handler = propertyOnly;
app.use(arrayWithProperty);
function replaced(req, res) { eval(req.query.code); }
const changed = [replaced];
changed[0] = (req, res) => {};
app.use(changed);
app.use([]);
const paths = ["/one", "/two"];
app.use(paths, first);
const unrelated = {use(value) { return value; }};
function notRegistered(req, res) { eval(req.query.code); }
unrelated.use([notRegistered]);
function errorHandler(error, req, res, next) {
  // ruleid: express-flow
  eval(req.body.code);
  eval(error.body.code);
  eval(res.body.code);
}
app.use([errorHandler]);
function inBranch(req, res) {
  // ruleid: express-flow
  eval(req.body.code);
}
let chosen;
if (flag) { chosen = [first]; } else { chosen = [inBranch]; }
app.use(chosen);
function objectOnly(req, res) { eval(req.query.code); }
const numericObject = {0: objectOnly, length: 1};
app.use(numericObject);
const partlyKnown = [first, unavailableHandler];
app.use(partlyKnown);
function pathOnly(req, res) { eval(req.query.code); }
const pathArguments = ["/prefix", pathOnly];
app.use(pathArguments, first);
const emptyHead = [[], pathOnly];
app.use(emptyHead, first);
const unknownHead = [unavailableHandler, pathOnly];
app.use(unknownHead, first);
function routeArray(req, res) {
  // ruleid: express-flow
  eval(req.query.code);
}
app.get("/empty-prefix", [[], routeArray]);
function afterUnknown(req, res) {
  // ruleid: express-flow
  eval(req.query.code);
}
app.get("/partial", [unavailableHandler, afterUnknown]);
