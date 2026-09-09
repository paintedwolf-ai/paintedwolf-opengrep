class Service {
  run(a) {
    a = 'safe';
    // ruleid: flow
    sink(arguments[0]);
  }
}
new Service().run(source());
