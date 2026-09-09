void main() {
  register((request) {
    // ruleid: flow
    sink(request);
    request = "fixed";
    sink(request);
  });
}
