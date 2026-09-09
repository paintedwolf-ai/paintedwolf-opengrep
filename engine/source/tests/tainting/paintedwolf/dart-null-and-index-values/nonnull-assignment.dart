String source() => "untrusted";
void sink(Object? value) {}
class Box { String text = "safe"; }
void run() {
 Box? box = Box();
 String x = "safe";
 box?.text = (x = source());
 // ruleid: flow
 sink(x);
 // ruleid: flow
 sink(box.text);
}
