String source() => "untrusted";
void sink(Object? value) {}
void run() {
 final xs = ["safe"];
 xs[0] = source();
 // ruleid: flow
 sink(xs[0]);
}
