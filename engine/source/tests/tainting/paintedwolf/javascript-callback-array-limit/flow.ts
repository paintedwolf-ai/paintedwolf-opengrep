import express from "express";
const app = express();
function safe(req, res) {}
function beforeLimit(req, res) {
  // ruleid: express-flow
  eval(req.query.code);
}
function afterLimit(req, res) { eval(req.query.code); }
const many = [safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, safe, beforeLimit, afterLimit];
app.get("/wide", many);
function tooDeep(req, res) { eval(req.query.code); }
app.get("/deep", [[[[[[[[[[[[[[[[[tooDeep]]]]]]]]]]]]]]]]]);
