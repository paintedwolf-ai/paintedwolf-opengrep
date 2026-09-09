function unsafe_field_write() {
  const object = { code: "1+1" };
  const alias = object;
  alias.code = source();
  // ruleid: alias-flow
  sink(object.code);
}
function safe_field_write() {
  const object = { code: source() };
  const alias = object;
  alias.code = "1+1";
  sink(object.code);
}
function safe_field_alias() {
  const object = { query: { code: source() } };
  const query = object.query;
  query.code = "1+1";
  sink(object.query.code);
}
function rebound_alias() {
  const object = { code: source() };
  let alias = object;
  alias = { code: "1+1" };
  alias.code = "2+2";
  // ruleid: alias-flow
  sink(object.code);
}
function uncertain_alias() {
  const object = { code: source() };
  const safe = { code: "1+1" };
  let alias = object;
  if (choice()) alias = safe;
  alias.code = "2+2";
  // ruleid: alias-flow
  sink(object.code);
}
function uncertain_write() {
  const object = { code: "1+1" };
  const other = { code: "2+2" };
  let alias = object;
  if (choice()) alias = other;
  alias.code = source();
  // ruleid: alias-flow
  sink(object.code);
  // ruleid: alias-flow
  sink(other.code);
}

function alternatives_do_not_alias_each_other() {
  const object = { code: "1+1" };
  const other = { code: "2+2" };
  let alias = object;
  if (choice()) alias = other;
  object.code = source();
  sink(other.code);
  // ruleid: alias-flow
  sink(alias.code);
}
function original_binding_replaced() {
  let object = { child: { code: "1+1" } };
  const child = object.child;
  const alias = object;
  object = { child: { code: "2+2" } };
  alias.child.code = source();
  // ruleid: alias-flow
  sink(child.code);
  sink(object.child.code);
}
function child_binding_replaced() {
  const object = { child: { code: source() } };
  const child = object.child;
  object.child = { code: "1+1" };
  child.code = source();
  sink(object.child.code);
  // ruleid: alias-flow
  sink(child.code);
}

function bracket_write() {
  const object = { code: "1+1" };
  const alias = object;
  alias["code"] = source();
  // ruleid: alias-flow
  sink(object.code);
}
function bracket_alias() {
  const object = { child: { code: source() } };
  const child = object["child"];
  child["code"] = "1+1";
  sink(object.child.code);
}

function replace_child_through_container_alias() {
  const object = { child: { code: source() } };
  const alias = object;
  const child = object.child;
  alias.child = { code: "1+1" };
  child.code = source();
  sink(object.child.code);
  // ruleid: alias-flow
  sink(child.code);
}
function replace_possible_child() {
  const object = { child: { code: "1+1" } };
  const child = object.child;
  object[choice()] = { code: source() };
  child.code = "2+2";
  // ruleid: alias-flow
  sink(object.child.code);
}
function mutate_possible_child() {
  const object = { child: { code: "safe" } };
  const child = object.child;
  object[choice()].code = source();
  // ruleid: alias-flow
  sink(child.code);
}
function clean_possible_child() {
  const object = { child: { code: source() } };
  const child = object.child;
  object[choice()].code = "safe";
  // ruleid: alias-flow
  sink(child.code);
}
function alias_possible_child() {
  const object = { child: { code: "safe" } };
  const child = object.child;
  const maybe = object[choice()];
  maybe.code = source();
  // ruleid: alias-flow
  sink(child.code);
}
function sanitize_possible_alias() {
  const object = { child: { code: source() } };
  const maybe = object[choice()];
  maybe.code = "safe";
  // ruleid: alias-flow
  sink(object.child.code);
}
