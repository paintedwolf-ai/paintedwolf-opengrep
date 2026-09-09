String source() => "untrusted";
void sink(Object? value) {}
void run() {
 String? x = null;
 // ruleid: flow
 sink(x ?? source());
}
