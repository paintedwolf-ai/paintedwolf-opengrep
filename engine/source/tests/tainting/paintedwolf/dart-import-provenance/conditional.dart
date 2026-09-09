import 'dart:io' if (dart.library.html) 'other.dart';
void run() {
  // ok: flow
  sink(HttpClient());
  // ok: flow
  sink(new HttpClient());
}
