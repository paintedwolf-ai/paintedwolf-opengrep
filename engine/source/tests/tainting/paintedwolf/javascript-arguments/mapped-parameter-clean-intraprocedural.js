function run(a) {
  a = 'safe';
  // ok: flow
  sink(arguments[0]);
}
run(source());
