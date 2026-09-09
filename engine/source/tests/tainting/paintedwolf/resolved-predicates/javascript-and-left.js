import {sameString as eq, invert as not} from "guards";
register(value => {
// ok: predicate
 const obj={left:value,right:source()}; if (eq(obj.left,"one") && eq(obj.right,"two")) sink(obj.left);
});
