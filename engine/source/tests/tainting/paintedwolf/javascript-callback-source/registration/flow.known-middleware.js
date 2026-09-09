const factory = require("express");
const middleware = factory.json();
middleware.get("/", (request, response) => { eval(request.query.code); });
