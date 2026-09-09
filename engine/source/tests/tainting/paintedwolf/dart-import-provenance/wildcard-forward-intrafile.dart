import 'dart:io';
void run() {
  // ok: flow
  sink(HttpClient());
  // ok: flow
  sink(new HttpClient());
}
class HttpClient {}
