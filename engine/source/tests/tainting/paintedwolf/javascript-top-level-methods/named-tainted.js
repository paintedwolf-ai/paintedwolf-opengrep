class Service {
  run(value) {
    // ruleid: method-flow
    sink(value);
  }
}
const instance = new Service();
instance.run(source());
