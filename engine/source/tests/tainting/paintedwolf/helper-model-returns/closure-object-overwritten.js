function test(){const callback=()=>{observe(canonical());};const obj={callback};obj.callback=()=>{};register(obj);}
