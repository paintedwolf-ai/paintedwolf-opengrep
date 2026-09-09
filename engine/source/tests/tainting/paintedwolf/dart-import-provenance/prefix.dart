import 'dart:io' as io;
void run() {
  // ruleid: flow
  sink(io.HttpClient());
  // ruleid: flow
  sink(new io.HttpClient());
}
void shadow(dynamic io) {
  // ok: flow
  sink(io.HttpClient());
}
