import 'dart:io' show HttpClient;
void run() {
  // ok: flow
  sink(HttpClient());
}
class HttpClient {}
