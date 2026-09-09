String source() => "untrusted";
void sink(Object? value) {}
void run() {
 final xs = [source(), "safe"];
 sink(xs[1]);
}
