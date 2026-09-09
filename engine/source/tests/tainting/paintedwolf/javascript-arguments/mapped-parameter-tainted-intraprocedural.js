function run(a) {
  a = source();
  // ok: flow
  sink(arguments[0]);
}
run('safe');
