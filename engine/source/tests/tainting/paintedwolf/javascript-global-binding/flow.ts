function external_input() {
  // ruleid: browser-input
  sink(location.search);
}
function parameter(location) {
  sink(location.search);
}
function lexical_binding() {
  const location = { search: "safe" };
  sink(location.search);
}
function before_hoisted_declaration() {
  sink(location.search);
  var location = { search: "safe" };
}
function nested_lexical_capture() {
  const read = () => sink(location.search);
  const location = { search: "safe" };
  read();
}
function sibling_scope() {
  { const location = { search: "safe" }; sink(location.search); }
  // ruleid: browser-input
  sink(location.search);
}
function destructured({location}) {
  sink(location.search);
}
function parameter_default(value = location.search) {
  var location = { search: "safe" };
  // ruleid: browser-input
  sink(value);
}
function catch_scope() {
  try {} catch (location) { sink(location.search); }
  // ruleid: browser-input
  sink(location.search);
}
function hoisted_block_var() {
  sink(location.search);
  { var location = { search: "safe" }; }
}
function destructured_local() {
  const { location } = { location: { search: "safe" } };
  sink(location.search);
}
function destructured_array() {
  const [location] = [{ search: "safe" }];
  sink(location.search);
}
function named_function_expression() {
  const handler = function location() { sink(location.search); };
  handler();
  // ruleid: browser-input
  sink(location.search);
}
function hoisted_loop_var() {
  sink(location.search);
  for (var location of [{ search: "safe" }]) {}
}
function lexical_loop_variable() {
  for (let location of [{ search: "safe" }]) { sink(location.search); }
  // ruleid: browser-input
  sink(location.search);
}
function named_class_expression() {
  const handler = class location { read() { sink(location.search); } };
  // ruleid: browser-input
  sink(location.search);
}
