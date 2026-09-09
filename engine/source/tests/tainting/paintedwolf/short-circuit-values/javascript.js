let safe = true || source();
sink(safe);
let unsafe = false || source();
// ruleid: flow
sink(unsafe);
let safe_and = false && source();
sink(safe_and);
let unsafe_and = true && source();
// ruleid: flow
sink(unsafe_and);
true || sink(source());
false && sink(source());
// ruleid: flow
false || sink(source());
// ruleid: flow
true && sink(source());
let chained_safe = false && source() && source();
sink(chained_safe);
let chained_or = true || source() || source();
sink(chained_or);
let chained_unsafe = false || false || source();
// ruleid: flow
sink(chained_unsafe);
let input = source();
let retained_safe = true || input;
sink(retained_safe);
let discarded = false && input;
sink(discarded);
let returned = false || input;
// ruleid: flow
sink(returned);
let selected = false || {unsafe: source(), safe: 'fixed'};
sink(selected.safe);
// ruleid: flow
sink(selected.unsafe);
let flag = true;
let changed = (flag = false) || source();
// ruleid: flow
sink(changed);
let changed_again = (flag = true) && source();
// ruleid: flow
sink(changed_again);
let nested = (false && input) || source();
// ruleid: flow
sink(nested);
