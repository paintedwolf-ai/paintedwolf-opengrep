import express from "express";
const app = express();
function first(req, res) { eval(req.query.code); }
const dotUse = [first];
dotUse.length = 0;
app.use(dotUse);
function second(req, res) { eval(req.query.code); }
const computedUse = [second];
computedUse["length"] = 0;
app.use(computedUse);
function third(req, res) { eval(req.query.code); }
const dotGet = [third];
dotGet.length = 0;
app.get("/dot", dotGet);
function fourth(req, res) { eval(req.query.code); }
const computedGet = [fourth];
computedGet["length"] = 0;
app.get("/computed", computedGet);
function retained(req, res) {
  // ruleid: express-flow
  eval(req.query.code);
}
const nonempty = [retained];
nonempty["length"] = 1;
app.use(nonempty);
