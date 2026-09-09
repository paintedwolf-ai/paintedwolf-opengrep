import 'dart.io' show HttpClient;
void run() {
 // ok: flow
 sink(HttpClient());
 // ok: flow
 sink(new HttpClient());
}
