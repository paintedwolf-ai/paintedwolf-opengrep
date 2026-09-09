const express=require('express');
const app=express();
app.set('port',8080);
// ok: flow
app.get('/',req=>sink('fixed'));
