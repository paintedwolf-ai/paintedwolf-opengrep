import express from "express";
const app=express();
app.set("host","127.0.0.1");
app.set("port",8080);
// ruleid: flow
app.get("/", (req,res)=>sink(req.query.command));
