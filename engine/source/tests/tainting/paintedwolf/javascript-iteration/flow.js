function iterate_values() {
  for (const value of [source()]) {
    // ruleid: alias-flow
    sink(value);
  }
}
function iterate_structured_values() {
  for (const value of [{ unsafe: source(), safe: "safe" }]) {
    sink(value.safe);
    // ruleid: alias-flow
    sink(value.unsafe);
  }
}
function iterate_keys() {
  for (const key in { value: source() }) {
    sink(key);
  }
}
function iterate_external_keys() {
  for (const key in source()) {
    // ruleid: alias-flow
    sink(key);
  }
}
function safe_values() {
  for (const value of ["safe", "safe"]) {
    sink(value);
  }
}
function mutate_element_alias() {
  const child = { code: "safe" };
  const array = [child];
  for (const value of array) { value.code = source(); }
  // ruleid: alias-flow
  sink(child.code);
}
function mutate_inline_element_alias() {
  const child = { code: "safe" };
  for (const value of [child]) { value.code = source(); }
  // ruleid: alias-flow
  sink(child.code);
}
function rebind_element_variable() {
  const child = { code: "safe" };
  for (let value of [child]) { value = { code: source() }; }
  sink(child.code);
}
