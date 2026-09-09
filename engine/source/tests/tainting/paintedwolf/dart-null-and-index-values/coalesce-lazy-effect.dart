String source() => "untrusted";
void sink(Object? value) {}
void run() {
 String? x = "safe";
 String y = "safe";
 final z = x ?? (y = source());
 sink(y); sink(z);
}
