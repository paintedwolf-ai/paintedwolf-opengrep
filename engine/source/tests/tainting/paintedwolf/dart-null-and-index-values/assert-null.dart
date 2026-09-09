String source() => "untrusted";
void sink(Object? value) {}
void run() {
 String? x = null;
 x!;
 sink(source());
}
