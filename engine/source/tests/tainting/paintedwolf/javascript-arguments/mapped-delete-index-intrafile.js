function run(a) {
  delete arguments[0];
  a = source();
  // ok: flow
  sink(arguments[0]);
}
run('safe');
