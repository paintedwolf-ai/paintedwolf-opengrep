import 'dart:io' show HttpClient;
import 'other.dart' hide HttpClient;
void run() {
 // ruleid: flow
 sink(HttpClient());
}
