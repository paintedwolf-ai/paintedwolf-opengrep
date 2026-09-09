String source() => "untrusted";
void sink(Object? value) {}
void run() {
 String? x = null;
 String y = "safe";
 final z = x ?? (y = source());
 // ruleid: flow
 sink(y);
 // ruleid: flow
 sink(z);
}
