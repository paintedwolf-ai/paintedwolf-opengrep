export function run(a) {
  a = 'safe';
  // ruleid: flow
  sink(arguments[0]);
}
run(source());
