class Service {
  run(value) {
    // ok: method-flow
    sink(value);
  }
}
new Service().run('safe');
