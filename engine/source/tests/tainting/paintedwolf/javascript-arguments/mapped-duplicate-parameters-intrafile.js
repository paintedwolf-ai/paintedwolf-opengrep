function run(a, a) {
  a = 'safe';
  // ok: flow
  sink(arguments[1]);
}
run('safe', source());
