String source() => "untrusted";
void sink(Object? value) {}
class Box { String text = "safe"; }
void run() {
 String? x = null;
 x ??= source();
 // ruleid: flow
 sink(x);
}
