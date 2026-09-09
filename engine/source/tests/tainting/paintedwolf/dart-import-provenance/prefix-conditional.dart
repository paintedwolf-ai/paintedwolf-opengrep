import 'dart:io' if (dart.library.html) 'other.dart' as io;
void run() {
  // ok: flow
  sink(io.HttpClient());
  // ok: flow
  sink(new io.HttpClient());
}
