import {sameString as eq, invert as not} from "guards";
register(value => {
// ruleid: predicate
 const obj={left:{child:value}}; if(eq(obj.left.child,"safe")) {const alias=obj["left"]; unknown(alias); sink(alias.child);}
});
