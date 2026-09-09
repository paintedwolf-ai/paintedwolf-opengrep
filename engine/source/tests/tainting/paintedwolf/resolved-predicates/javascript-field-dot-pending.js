import {sameString as eq, invert as not} from "guards";
register(value => {
// ruleid: predicate
 const obj={left:value}; const allowed=eq(obj["left"],"safe"); obj.left=source(); if(allowed)sink(obj.left);
});
