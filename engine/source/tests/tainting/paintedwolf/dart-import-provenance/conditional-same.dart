import 'dart:io' if (dart.library.html) 'dart:io';
void run() {
  // ruleid: flow
  sink(HttpClient());
  // ruleid: flow
  sink(new HttpClient());
}
