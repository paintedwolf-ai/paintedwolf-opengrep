import {sameString as eq, invert as not} from "guards";
register(value => {
// ruleid: predicate
 const obj = {left:value, right:source()}; if (eq(obj.left,"safe")) {obj.left=source(); sink(obj.left);}
});
