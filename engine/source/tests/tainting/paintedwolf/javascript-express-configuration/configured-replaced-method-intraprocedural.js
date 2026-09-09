import express from "express";
const app=express();
app.set=function(){this.get=function(path,handler){handler({query:{command:"fixed"}},{});};};
app.set("port",8080);
app.get("/", (req,res)=>sink(req.query.command));
