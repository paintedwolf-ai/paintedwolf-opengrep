function run(a) {
  Object.defineProperty(arguments, '0', {value: 'safe', writable: false});
  a = source();
  // ok: flow
  sink(arguments[0]);
}
run('safe');
