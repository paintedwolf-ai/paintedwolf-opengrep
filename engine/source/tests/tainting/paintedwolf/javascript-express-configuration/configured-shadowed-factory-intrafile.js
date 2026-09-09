import express from "express";
function configure(express){const app=express(); app.set("port",8080); app.get("/",(req,res)=>sink(req.query.command));}
