import 'dart:io' as io;
import 'other.dart' as io hide HttpClient;
void run() {
  // ruleid: flow
  sink(io.HttpClient());
  // ruleid: flow
  sink(new io.HttpClient());
}
