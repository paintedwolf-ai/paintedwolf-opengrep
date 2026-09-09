const factory = require("express");
unknown(factory);
const direct = factory();
direct.get("/", (request, response) => {
  // ruleid: express-flow
  eval(request.query.code);
});
const router = factory.Router();
router.get("/", (request, response) => { eval(request.query.code); });
