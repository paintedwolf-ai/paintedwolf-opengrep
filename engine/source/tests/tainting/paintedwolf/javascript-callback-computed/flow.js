import express from "express";
const app = express();
function literal({["query"]: input, ...rest}) {
  // ruleid: express-flow
  eval(input.code);
  eval(rest.query.code);
  // ruleid: express-flow
  eval(rest.body.code);
}
app.get("/literal", literal);
function unknown({[selectKey()]: input, ...rest}) {
  eval(input.code);
  eval(rest.query.code);
}
app.get("/unknown", unknown);
function knownBesideUnknown({query, [selectKey()]: input, ...rest}) {
  // ruleid: express-flow
  eval(query.code);
  eval(rest.query.code);
  eval(rest.body.code);
}
app.get("/mixed", knownBesideUnknown);
