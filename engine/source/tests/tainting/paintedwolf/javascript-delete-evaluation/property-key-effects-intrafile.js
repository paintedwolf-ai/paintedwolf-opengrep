function test(object) {
  // ruleid: delete-evaluation
  delete object[sink(source())];
}
