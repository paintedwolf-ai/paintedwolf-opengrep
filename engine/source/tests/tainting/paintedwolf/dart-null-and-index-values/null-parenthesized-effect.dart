String source() => "untrusted";
void sink(Object? value) {}
class Box {
 Box get next => this;
 void send(Object? value) {}
}
Box? unknownBox() => null;
void run() {
 Box? box = null;
 String x = "safe";
 (box?.next)?.send(x = source());
 sink(x);
}
