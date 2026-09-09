// ruleid: method-formals
class Service {
  run(value) {
    value = 'safe';
    // ruleid: argument-syntax
    sink(arguments[0]);
  }
}
