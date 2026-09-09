String source() => "untrusted";
void sink(Object? value) {}
class Box {
 Box get next => this;
 void send(Object? value) {}
}
Box? unknownBox() => null;
void run() {
 Box? box = Box();
 String x = "safe";
 // ruleid: flow
 box?.send(x = source());
 // ruleid: flow
 sink(x);
}
