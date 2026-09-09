import 'dart:io';
import 'other.dart' hide HttpClient;
void run() {
  // ruleid: flow
  sink(HttpClient());
  // ruleid: flow
  sink(new HttpClient());
}
