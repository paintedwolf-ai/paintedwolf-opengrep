import 'dart:io' hide HttpClient;
void run() {
  // ok: flow
  sink(HttpClient());
  // ok: flow
  sink(new HttpClient());
}
