class Service {
  run(value) {
    // ok: method-flow
    sink(value);
  }
}
const instance = new Service();
instance.run('safe');
