String source() => "untrusted";
void sink(Object? value) {}
void run() {
 final xs = ["safe"];
 final ys = xs;
 ys[0] = source();
 // ruleid: flow
 sink(xs[0]);
}
