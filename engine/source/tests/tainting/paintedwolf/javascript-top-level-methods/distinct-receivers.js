class First {
  run(value) {
    // ok: method-flow
    sink(value);
  }
}
class Second {
  run(value) {
    // ruleid: method-flow
    sink(value);
  }
}
const first = new First();
const second = new Second();
first.run('safe');
second.run(source());
