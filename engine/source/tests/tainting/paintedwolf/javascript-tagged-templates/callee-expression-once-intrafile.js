let calls=0;
function getTag(){calls++; return (strings,value)=>value;}
// ruleid: flow
sink(getTag()`${source()}`);
