function store_reference() {
  const child = { code: "safe" };
  const object = { child };
  child.code = source();
  // ruleid: alias-flow
  sink(object.child.code);
}
function clean_reference() {
  const child = { code: source() };
  const object = { child };
  object.child.code = "safe";
  sink(child.code);
}
function array_reference() {
  const child = { code: "safe" };
  const array = [child];
  array[0].code = source();
  // ruleid: alias-flow
  sink(child.code);
}
function copied_scalar() {
  const original = { code: source() };
  const copy = { code: original.code };
  copy.code = "safe";
  // ruleid: alias-flow
  sink(original.code);
}
function shallow_spread() {
  const child = { code: "safe" };
  const original = { child, code: "safe" };
  const copy = { ...original };
  copy.code = source();
  sink(original.code);
  child.code = source();
  // ruleid: alias-flow
  sink(copy.child.code);
}
function spread_overwrite() {
  const child = { code: "safe" };
  const original = { child };
  const copy = { ...original, child: { code: "safe" } };
  child.code = source();
  sink(copy.child.code);
}
function retain_old_literal_reference() {
  let object = { code: "safe" };
  const old = object;
  object = { child: object };
  old.code = source();
  // ruleid: alias-flow
  sink(object.child.code);
  sink(object.code);
}
function overwrite_spread_source() {
  let object = { child: { code: "safe" }, code: "safe" };
  const old = object;
  object = { ...object };
  object.code = source();
  sink(old.code);
  old.child.code = source();
  // ruleid: alias-flow
  sink(object.child.code);
}
