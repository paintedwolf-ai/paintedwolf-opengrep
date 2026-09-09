function run(a = 'safe') {
  a = 'safe';
  // ruleid: flow
  sink(arguments[0]);
}
run(source());
