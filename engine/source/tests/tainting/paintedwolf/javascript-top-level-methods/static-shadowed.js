class Service {
  static run(value) { sink(value); }
}
function invoke(Service) {
  Service.run(source());
}
invoke({run(value) { return "safe"; }});
