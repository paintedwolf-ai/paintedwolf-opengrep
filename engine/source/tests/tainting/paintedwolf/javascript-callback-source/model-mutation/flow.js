import express from "express";
function replace(server) { server.get = (_path, callback) => "fixed"; }
const changed = express();
replace(changed);
changed.get("/", req => eval(req.query.code));
const escaped = express();
unknownMutation(escaped);
escaped.get("/", req => eval(req.query.code));
const pure = express();
function observe(server) { return 1; }
observe(pure);
// ruleid: express-flow
pure.get("/", req => eval(req.query.code));
// ruleid: express-flow
pure.get("/again", req => eval(req.query.code));
const aliased = express();
const alias = aliased;
replace(alias);
aliased.get("/", req => eval(req.query.code));
const contained = express();
const object = {server: contained};
unknownMutation(object);
contained.get("/", req => eval(req.query.code));
const inArray = express();
const array = [inArray];
unknownMutation(array);
inArray.get("/", req => eval(req.query.code));
const receiver = express();
receiver.unknownMethod();
receiver.get("/", req => eval(req.query.code));
const constructorArgument = express();
new Unreviewed(constructorArgument);
constructorArgument.get("/", req => eval(req.query.code));
const alternative = express();
if (condition) replace(alternative);
alternative.get("/", req => eval(req.query.code));
const independent = express();
// ruleid: express-flow
independent.get("/", req => eval(req.query.code));
const hiddenEffect = express();
function defaultEffect(server, ignored = replace(server)) { return 1; }
defaultEffect(hiddenEffect);
hiddenEffect.get("/", req => eval(req.query.code));
const aliasPure = express();
const noEffect = observe;
noEffect(aliasPure);
// ruleid: express-flow
aliasPure.get("/", req => eval(req.query.code));
const rewritten = express();
rewritten.get = (_path, callback) => "fixed";
rewritten.get("/", req => eval(req.query.code));
const outer = express();
const inner = express();
outer.child = inner;
unknownMutation(outer);
outer.child.get("/", req => eval(req.query.code));
inner.get("/", req => eval(req.query.code));
const captured = express();
function capturedReplacement() { captured.get = (_path, callback) => "fixed"; }
unknownMutation(capturedReplacement);
captured.get("/", req => eval(req.query.code));
