import express from "express";
const conditional = express();
if (condition) conditional.get = (_path, callback) => "fixed";
// ruleid: express-flow
conditional.post("/", req => eval(req.query.code));
conditional.get("/", req => eval(req.query.code));
const definite = express();
definite.get = (_path, callback) => "fixed";
// ruleid: express-flow
definite.post("/", req => eval(req.query.code));
definite.get("/", req => eval(req.query.code));
const captured = express();
function replaceCaptured() { captured.get = (_path, callback) => "fixed"; }
maybeInvoke(replaceCaptured);
// ruleid: express-flow
captured.post("/", req => eval(req.query.code));
captured.get("/", req => eval(req.query.code));
