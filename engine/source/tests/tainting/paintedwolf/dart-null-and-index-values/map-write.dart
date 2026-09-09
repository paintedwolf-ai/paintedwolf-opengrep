String source() => "untrusted";
void sink(Object? value) {}
void run() {
 final xs = {"x": "safe"};
 xs["x"] = source();
 // ruleid: flow
 sink(xs["x"]);
}
