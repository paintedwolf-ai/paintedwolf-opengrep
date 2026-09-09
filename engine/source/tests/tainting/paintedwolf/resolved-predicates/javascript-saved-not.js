import {sameString as eq, invert as not} from "guards";
register(value => {
// ok: predicate
 const allowed=eq(value,"safe"); const rejected=!allowed; if(!rejected) sink(value);
});
