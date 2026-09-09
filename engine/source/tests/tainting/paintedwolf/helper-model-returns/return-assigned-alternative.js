function fresh(f){let x;if(f)x=canonical();else x=trusted();return x;} function test(flag){
// ruleid: model
observe(fresh(flag));}
