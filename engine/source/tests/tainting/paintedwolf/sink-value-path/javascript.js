function queries(flag) {
  // ruleid: flow
  sink([source(), "bound"]);
  sink(["SELECT ?", source()]);
  let query = [source(), "bound"];
  // ruleid: flow
  sink(query);
  query = ["SELECT ?", source()];
  sink(query);
  const alias = query;
  alias[0] = source();
  // ruleid: flow
  sink(query);
  alias[0] = "SELECT ?";
  sink(query);
  if (flag) query = [source(), "bound"];
  // ruleid: flow
  sink(query);
  const value = source();
  // ruleid: flow
  sink(value);
  sink([]);
  sink(["fixed", [source()]]);
  // ruleid: flow
  sink([[source()], "fixed"]);
}
