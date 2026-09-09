class Service {
  static run(value) {
    // ok: method-flow
    sink(value);
  }
}
Service.run('safe');
