import {sameString as eq, invert as not} from "guards";
register(value => {
 let allowed=eq(value,"safe");
 // ruleid: predicate
 callbackSink(value,()=>allowed=true);
 // ruleid: predicate
 if(allowed)sink(value);
});
