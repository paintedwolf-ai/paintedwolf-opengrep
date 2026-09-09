import 'dart:io' show HttpClient;
void run() {
  // ruleid: flow
  sink(HttpClient());
  // ruleid: flow
  sink(new HttpClient());
  // ok: flow
  sink(Other());
}
