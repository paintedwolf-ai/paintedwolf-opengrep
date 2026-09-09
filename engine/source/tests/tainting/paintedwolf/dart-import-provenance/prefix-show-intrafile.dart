import 'dart:io' as io show HttpClient;
void run() {
  // ruleid: flow
  sink(io.HttpClient());
  // ruleid: flow
  sink(new io.HttpClient());
}
