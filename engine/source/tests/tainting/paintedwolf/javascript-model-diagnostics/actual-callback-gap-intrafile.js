const express=require('express');
const app=express();
const unknownApp=unrelated(app);
unknownApp.get('/',req=>sink(req.query.code));
