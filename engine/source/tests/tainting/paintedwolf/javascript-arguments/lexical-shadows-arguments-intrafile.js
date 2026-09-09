function run() {
  let arguments = ['safe'];
  // ok: flow
  sink(arguments[0]);
}
run(source());
