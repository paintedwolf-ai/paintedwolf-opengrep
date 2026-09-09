function overwrites(flag) {
  const value = source();
  value.query = { text: "fixed", bound: "safe" };
  sink(value.query.text);
  // ruleid: flow
  sink(value.other);
  const alias = value.query;
  alias.text = source();
  // ruleid: flow
  sink(value.query.text);
  sink(value.query.bound);
  // ruleid: flow
  sink(value.query);
  value.query = { text: "fixed", bound: source() };
  sink(value.query.text);
  // ruleid: flow
  sink(value.query.bound);
  // ruleid: flow
  sink(value.query);
  if (flag) value.query = source();
  // ruleid: flow
  sink(value.query.text);
}
