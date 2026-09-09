import {sameString as eq, invert as not} from "guards";
register(value => {
// ok: predicate
 if (eq(value,"one") || eq(value,"two")) sink(value);
});
