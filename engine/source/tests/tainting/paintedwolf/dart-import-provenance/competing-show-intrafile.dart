import 'dart:io';
import 'other.dart' show Platform;
void run() {
  // ruleid: flow
  sink(HttpClient());
  // ruleid: flow
  sink(new HttpClient());
}
