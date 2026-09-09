String source() => "untrusted";
void sink(Object? value) {}
void run() {
 String? x = source();
 // ruleid: flow
 sink(x!);
}
