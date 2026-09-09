import 'dart:io' deferred as io hide HttpClient;
void run() {
  // ok: flow
  sink(io.HttpClient());
  // ok: flow
  sink(new io.HttpClient());
}
