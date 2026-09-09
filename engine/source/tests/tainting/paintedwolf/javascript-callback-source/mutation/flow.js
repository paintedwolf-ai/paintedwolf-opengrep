import express from "express";
const app = express();
function removed(req, res) { eval(req.query.code); }
const handlers = [removed, (req, res) => {}];
const alias = handlers;
handlers.shift();
app.use(alias);
function shortened(req, res) { eval(req.query.code); }
const limited = [shortened];
limited.length = 0;
app.get("/shortened", limited);
function returned(req, res) {
  // ruleid: express-flow
  eval(req.query.code);
}
function build() { return [returned]; }
app.use(build());
function escaped(req, res) { eval(req.query.code); }
const escapedArray = [escaped];
unknownMutation(escapedArray);
app.use(escapedArray);
function kept(req, res) {
  // ruleid: express-flow
  eval(req.body.code);
}
function safeFactory() { return []; }
function fieldFactory() { return [kept]; }
app.use(safeFactory());
app.get("/field", fieldFactory()[0]);
function rejected(req, res) { eval(req.body.code); }
const actual = [rejected];
const unrelated = {use(value) { unknownMutation(value); }};
unrelated.use(actual);
app.get("/unproven-model", actual);
function wrapped(req, res) { eval(req.query.code); }
const wrappedArray = [wrapped];
const box = {callbacks: wrappedArray};
unknownMutation(box);
app.use(wrappedArray);
function inlineWrapped(req, res) { eval(req.body.code); }
const inlineArray = [inlineWrapped];
unknownMutation({callbacks: inlineArray});
app.use(inlineArray);
function computedLength(req, res) { eval(req.query.code); }
const computedArray = [computedLength];
computedArray["length"] = 0;
app.use(computedArray);
function nestedEscaped(req, res) { eval(req.body.code); }
const inner = [nestedEscaped];
const outer = [inner];
unknownMutation(outer);
app.use(inner);
function objectInArray(req, res) { eval(req.query.code); }
const objectArray = [objectInArray];
unknownMutation([{callbacks: objectArray}]);
app.use(objectArray);
