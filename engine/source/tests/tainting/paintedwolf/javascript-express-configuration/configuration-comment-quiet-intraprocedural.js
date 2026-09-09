import express from "express";
const app=express();
app.set("port",8080);
function handler(req,res){sink(req.query.command);}
// app.get("/",handler);
