String source() => "untrusted";
void sink(Object? value) {}
class Box { String text = "safe"; }
void run() {
 Box? box = null;
 String x = "safe";
 final assigned = box?.text = (x = source());
 sink(x);
 sink(assigned);
}
