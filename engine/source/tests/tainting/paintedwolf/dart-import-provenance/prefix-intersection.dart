import 'dart:io' as io show HttpClient, Platform show Platform;
void run() {
  // ok: flow
  sink(io.HttpClient());
  // ok: flow
  sink(new io.HttpClient());
}
