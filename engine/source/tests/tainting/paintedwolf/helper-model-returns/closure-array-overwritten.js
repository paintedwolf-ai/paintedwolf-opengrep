function test(){const callback=()=>{observe(canonical());};const list=[callback];list[0]=()=>{};register(list);}
