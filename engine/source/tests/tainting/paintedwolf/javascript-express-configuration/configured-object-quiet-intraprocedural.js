import express from "express";
const app={set(name,value){},get(path,handler){handler({query:{command:"fixed"}},{});}};
app.set("port",8080);
app.get("/", (req,res)=>sink(req.query.command));
