const express=require('express');
const app=express();
const unknownApp=unrelated(app);
unknownApp.set('port',8080);
// ok: flow
sink('fixed');
