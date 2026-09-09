import {sameString as eq, invert as not} from "guards";
register(value => {
// ruleid: predicate
 const allowed=eq(value,"safe"); sink("fixed"); if(allowed)sink(value);
});
