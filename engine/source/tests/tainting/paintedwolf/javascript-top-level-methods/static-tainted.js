class Service {
  static run(value) {
    // ruleid: method-flow
    sink(value);
  }
}
Service.run(source());
