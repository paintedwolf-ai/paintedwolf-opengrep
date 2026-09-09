String source() => "untrusted";
void sink(Object? value) {}
void run() {
 final xs = {"x": source()};
 final ys = xs;
 ys["x"] = "safe";
 sink(xs["x"]);
}
