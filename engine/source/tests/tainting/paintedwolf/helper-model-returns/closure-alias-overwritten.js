function test(){const callback=()=>{observe(canonical());};let copy=callback;copy=()=>{};register(copy);}
