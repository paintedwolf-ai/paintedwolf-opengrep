String source() => "untrusted";
void sink(Object? value) {}
class Box { String text = "safe"; }
void run() {
 final x = <String,String?>{"v": null};
 final y = x;
 y["v"] ??= source();
 // ruleid: flow
 sink(x["v"]);
}
