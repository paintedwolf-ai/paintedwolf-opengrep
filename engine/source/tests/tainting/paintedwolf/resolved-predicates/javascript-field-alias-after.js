import {sameString as eq, invert as not} from "guards";
register(value => {
// ruleid: predicate
 const obj = {left:value, right:source()}; if (eq(obj.left,"safe")) {const alias=obj; mutate(alias); sink(alias.left);}
});
