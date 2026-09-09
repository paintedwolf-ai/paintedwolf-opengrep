import express from "express";
const app = express();
app.get("/value", (request, response) => {
  const value = request.query.code;
  // ruleid: express-flow
  eval(value);
});
const router = app;
router.get("/alias", (request, response) => {
  // ruleid: express-flow
  eval(request.query.code);
});

const object = { query: { code: "1+1" } };
eval(object.query.code);
function unrelated(express) {
  const local = express();
  local.get("/", (request, response) => {
    eval(request.query.code);
  });
}
app.get("/overwritten", (request, response) => {
  request = { query: { code: "1+1" } };
  eval(request.query.code);
});
app.get("/field", (request, response) => {
  request.query.code = "1+1";
  eval(request.query.code);
});
app.get("/query-alias", (request, response) => {
  const query = request.query;
  query.code = "1+1";
  eval(query.code);
});
app.get("/method", (request, response) => {
  eval(request.method);
});

app.get("/sibling", (request, response) => {
  request.query.safe = "1+1";
  // ruleid: express-flow
  eval(request.query.code);
});
app.get("/branch", (request, response) => {
  if (choice()) request.query.code = "1+1";
  // ruleid: express-flow
  eval(request.query.code);
});
app.get("/retainted", (request, response) => {
  request.query.code = "1+1";
  request.query.code = request.body.code;
  // ruleid: express-flow
  eval(request.query.code);
});

app.get("/both-branches", (request, response) => {
  if (choice()) request.query.code = "1+1";
  else request.query.code = "2+2";
  eval(request.query.code);
});
app.get("/loop", (request, response) => {
  while (choice()) request.query.code = "1+1";
  // ruleid: express-flow
  eval(request.query.code);
});
app.get("/unknown-key", (request, response) => {
  request.query[choice()] = "1+1";
  // ruleid: express-flow
  eval(request.query.code);
});

app.get("/unknown-key-number", (request, response) => {
  request.query[choice()] = 0;
  // ruleid: express-flow
  eval(request.query.code);
});
