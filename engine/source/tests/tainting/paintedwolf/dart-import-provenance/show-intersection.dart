import 'dart:io' show HttpClient, Platform show Platform;
void run() {
  // ok: flow
  sink(HttpClient());
  // ok: flow
  sink(new HttpClient());
}
