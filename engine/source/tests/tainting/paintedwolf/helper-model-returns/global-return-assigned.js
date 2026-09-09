function fresh(){return canonical();}
function test(){const x=fresh();
// ruleid: model
observe(x);
}
