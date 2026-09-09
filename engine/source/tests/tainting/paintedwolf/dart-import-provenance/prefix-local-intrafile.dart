import 'dart:io' as io;
class io { static HttpClient() => Object(); }
void run() {
  // ok: flow
  sink(io.HttpClient());
  // ok: flow
  sink(new io.HttpClient());
}
