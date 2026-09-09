const express=require('express');
const app=express();
app.set('port',8080);
// ruleid: flow
app.get('/',req=>sink(req.query.code));
