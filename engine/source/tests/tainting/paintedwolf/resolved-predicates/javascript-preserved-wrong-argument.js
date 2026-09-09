import {sameString as eq, invert as not} from "guards";
register(value => {
// ruleid: predicate
 if(eq(value,"safe")) {secondSink(value,"fixed");sink(value);}
});
