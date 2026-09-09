String source() => "untrusted";
void sink(Object? value) {}
void run() {
 String? x = "safe";
 sink(x!);
}
