import express from "express";
const app=express();
app.set("view engine","pug");
app.enable("trust proxy");
app.disable("x-powered-by");
app.enabled("trust proxy");
app.disabled("x-powered-by");
app.get("port");
app.engine("html", renderer);
// ruleid: flow
app.get("/", (req,res)=>sink(req.query.command));
