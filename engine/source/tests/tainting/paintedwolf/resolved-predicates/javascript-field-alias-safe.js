import {sameString as eq, invert as not} from "guards";
register(value => {
// ok: predicate
 const obj = {left:value, right:source()}; const alias=obj; if (eq(obj.left,"safe")) sink(alias.left);
});
