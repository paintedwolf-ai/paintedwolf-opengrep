function unknownWrite(key) {
  const value = {unsafe: source()};
  value[key] = "fixed";
  // ruleid: unknown-write
  sink(value.unsafe);
}
function knownOtherField() {
  const value = {unsafe: source()};
  value.safe = "fixed";
  // ruleid: unknown-write
  sink(value.unsafe);
}
function knownOverwrite() {
  const value = {unsafe: source()};
  value.unsafe = "fixed";
  // ok: unknown-write
  sink(value.unsafe);
}
function unknownTaintedWrite(key) {
  const value = {safe: "fixed"};
  value[key] = source();
  // ruleid: unknown-write
  sink(value.safe);
}
function unknownSafeWrite(key) {
  const value = {safe: "fixed"};
  value[key] = "fixed";
  // ok: unknown-write
  sink(value.safe);
}

function taintedParent(key) {
  const value = source();
  value[key] = "fixed";
  // ruleid: unknown-write
  sink(value.unsafe);
}
function nestedUnknownWrite(key) {
  const value = {nested: {unsafe: source()}};
  value[key] = {unsafe: "fixed"};
  // ruleid: unknown-write
  sink(value.nested.unsafe);
}
function repeatedUnknownWrite(key, condition) {
  const value = {unsafe: source()};
  while (condition) {
    value[key] = "fixed";
  }
  // ruleid: unknown-write
  sink(value.unsafe);
}
function knownKeyThroughVariable() {
  const value = {unsafe: source()};
  const key = "unsafe";
  value[key] = "fixed";
  // ok: unknown-write
  sink(value.unsafe);
}
function reassignedKey(condition) {
  const value = {unsafe: source()};
  let key = "unsafe";
  if (condition) { key = "other"; }
  value[key] = "fixed";
  // ruleid: unknown-write
  sink(value.unsafe);
}
function constantOtherKey() {
  const value = {unsafe: source()};
  const key = "other";
  value[key] = "fixed";
  // ruleid: unknown-write
  sink(value.unsafe);
}
function constantNumericKey() {
  const value = [source(), "fixed"];
  const key = 0;
  value[key] = "fixed";
  // ok: unknown-write
  sink(value[0]);
}
