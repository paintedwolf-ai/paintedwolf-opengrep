String source() => "untrusted";
void sink(Object? value) {}
void run() {
 final xs = [source()];
 // ruleid: flow
 sink(xs[0]);
}
