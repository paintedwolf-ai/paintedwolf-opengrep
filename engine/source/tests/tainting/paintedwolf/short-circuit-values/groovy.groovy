def safe = true || source();
sink(safe);
def unsafe = false || source();
// ruleid: flow
sink(unsafe);
def safe_and = false && source();
sink(safe_and);
def unsafe_and = true && source();
// ruleid: flow
sink(unsafe_and);
true || sink(source());
false && sink(source());
// ruleid: flow
false || sink(source());
// ruleid: flow
true && sink(source());
def chained_safe = false && source() && source();
sink(chained_safe);
def chained_or = true || source() || source();
sink(chained_or);
def chained_unsafe = false || false || source();
// ruleid: flow
sink(chained_unsafe);
