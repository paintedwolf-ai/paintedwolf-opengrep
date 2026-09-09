String source() => "untrusted";
void sink(Object? value) {}
void run() {
 final xs = {"x": source()};
 xs["x"] = "safe";
 sink(xs["x"]);
}
