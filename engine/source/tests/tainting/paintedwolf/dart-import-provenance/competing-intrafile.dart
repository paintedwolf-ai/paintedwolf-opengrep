import 'dart:io';
import 'other.dart';
void run() {
  // ok: flow
  sink(HttpClient());
  // ok: flow
  sink(new HttpClient());
}
