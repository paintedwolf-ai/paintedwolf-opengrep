String source() => "untrusted";
void sink(Object? value) {}
void run() {
 final xs = {"x": "safe"};
 sink(xs[source()]);
}
