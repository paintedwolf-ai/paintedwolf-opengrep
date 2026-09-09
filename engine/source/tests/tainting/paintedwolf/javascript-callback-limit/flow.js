import express from "express";
const app = express();
function install(callback) {
  app.get("/", callback);
}
install(externalHandler);
eval("constant");
