String source() => "untrusted";
void sink(Object? value) {}
void run() {
 final xs = {"x": source()};
 // ruleid: flow
 sink(xs["x"]!);
}
