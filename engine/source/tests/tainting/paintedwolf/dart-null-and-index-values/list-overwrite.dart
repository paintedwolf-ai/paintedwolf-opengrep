String source() => "untrusted";
void sink(Object? value) {}
void run() {
 final xs = [source()];
 xs[0] = "safe";
 sink(xs[0]);
}
