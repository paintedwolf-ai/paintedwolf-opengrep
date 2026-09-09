String source() => "untrusted";
void sink(Object? value) {}
void run() {
 final xs = {"x": "safe"};
 final ys = xs;
 ys["x"] = source();
 // ruleid: flow
 sink(xs["x"]);
}
