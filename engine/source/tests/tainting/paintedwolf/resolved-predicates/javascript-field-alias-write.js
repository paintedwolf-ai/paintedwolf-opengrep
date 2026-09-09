import {sameString as eq, invert as not} from "guards";
register(value => {
// ruleid: predicate
 const obj = {left:value, right:source()}; const alias=obj; if (eq(obj.left,"safe")) {alias.left=source(); sink(obj.left);}
});
