import 'dart.io' as io;
void run() {
 // ok: flow
 sink(io.HttpClient());
 // ok: flow
 sink(new io.HttpClient());
}
