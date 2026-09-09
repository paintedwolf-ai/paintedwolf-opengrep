String source() => "untrusted";
void sink(Object? value) {}
void run() {
 String? x = null;
 final y = x ?? "safe" ?? source();
 sink(y);
}
