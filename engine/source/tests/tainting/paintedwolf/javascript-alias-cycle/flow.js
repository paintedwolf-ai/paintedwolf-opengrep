function cycle() {
  const object = { code: source() };
  object.self = object;
  // ruleid: alias-flow
  sink(object.self.code);
}
