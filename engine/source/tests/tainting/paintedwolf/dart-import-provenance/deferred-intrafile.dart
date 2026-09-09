import 'dart:io' deferred as io show HttpClient;
void run() {
  // ruleid: flow
  sink(io.HttpClient());
  // ruleid: flow
  sink(new io.HttpClient());
}
