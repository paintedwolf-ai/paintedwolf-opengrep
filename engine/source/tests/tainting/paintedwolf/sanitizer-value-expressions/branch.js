function check(flag) { let value = typed(); if (flag) value = untyped();
// ruleid: flow
sink(sanitize(value));
}
