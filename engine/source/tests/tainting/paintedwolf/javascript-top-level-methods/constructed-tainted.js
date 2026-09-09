class Service {
  run(value) {
    // ruleid: method-flow
    sink(value);
  }
}
new Service().run(source());
