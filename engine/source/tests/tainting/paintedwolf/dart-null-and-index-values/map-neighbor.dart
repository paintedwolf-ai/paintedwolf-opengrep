String source() => "untrusted";
void sink(Object? value) {}
void run() {
 final xs = {"x": source(), "y": "safe"};
 sink(xs["y"]);
}
