String source() => "untrusted";
void sink(Object? value) {}
void run() {
 final x = "safe" ?? source();
 sink(x);
}
