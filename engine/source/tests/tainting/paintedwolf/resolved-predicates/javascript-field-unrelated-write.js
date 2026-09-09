import {sameString as eq, invert as not} from "guards";
register(value => {
// ok: predicate
 const obj = {left:value, right:source()}; if (eq(obj.left,"safe")) {obj.right="fixed"; sink(obj.left);}
});
