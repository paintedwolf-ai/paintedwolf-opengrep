import express from "express";
const app=express();
app.set("port",8080);
app.get("/", (req,res)=>sink("fixed"));
