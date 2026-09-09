import {sameString as eq, invert as not} from "guards";
register(value => {
// ok: predicate
 if (!not(eq(value, "safe"))) sink(value);
});
