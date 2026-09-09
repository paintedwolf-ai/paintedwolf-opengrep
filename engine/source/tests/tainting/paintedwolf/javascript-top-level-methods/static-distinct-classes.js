class First {
  static run(value) { sink(value); }
}
class Second {
  static run(value) {
    // ruleid: method-flow
    sink(value);
  }
}
First.run("safe");
Second.run(source());
